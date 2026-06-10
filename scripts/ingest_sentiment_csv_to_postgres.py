"""Ingest local sentiment CSV archives into PostgreSQL.

Idempotent behavior:
- `news_sentiment`: inserts only rows whose natural key is not already present
  (ticker, headline, source, published_at, url).
- `sentiment_summary`: upserts on (ticker, analysis_date).
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional

import pandas as pd
from sqlalchemy import create_engine, text


sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def _get_engine():
    from modules.database.factory import get_backend

    backend = get_backend()
    if backend.__class__.__name__ != "PostgreSQLBackend":
        raise RuntimeError("Expected PostgreSQLBackend; set DATABASE_BACKEND=postgresql")

    return create_engine(str(getattr(backend, "connection_url")))


def _load_news_df(sentiment_dir: Path) -> pd.DataFrame:
    files = sorted(sentiment_dir.glob("news_analyzed_*.csv"))
    if not files:
        return pd.DataFrame()

    parts = []
    for fp in files:
        try:
            df = pd.read_csv(fp)
        except Exception:
            continue
        if df.empty:
            continue
        df["_src_file"] = fp.name
        parts.append(df)

    if not parts:
        return pd.DataFrame()

    df = pd.concat(parts, ignore_index=True)

    out = pd.DataFrame(
        {
            "ticker": df.get("symbol", pd.Series(dtype=str)).astype(str).str.upper().str.strip(),
            "headline": df.get("title", pd.Series(dtype=str)).astype(str).str.strip(),
            "source": df.get("source", pd.Series(dtype=str)).astype(str).str.strip(),
            "published_at": pd.to_datetime(df.get("published_at", pd.Series(dtype=str)), errors="coerce"),
            "sentiment_score": pd.to_numeric(df.get("sentiment_score", pd.Series(dtype=float)), errors="coerce"),
            "sentiment_label": df.get("sentiment_label", pd.Series(dtype=str)).astype(str).str.strip(),
            "relevance_score": pd.to_numeric(df.get("subjectivity", pd.Series(dtype=float)), errors="coerce"),
            "url": df.get("url", pd.Series(dtype=str)).astype(str).str.strip(),
        }
    )

    out = out[(out["ticker"] != "") & (out["headline"] != "")]
    out = out.dropna(subset=["published_at"])
    out = out.drop_duplicates(subset=["ticker", "headline", "source", "published_at", "url"], keep="last")
    return out.reset_index(drop=True)


def _analysis_date_from_row(row: pd.Series) -> Optional[pd.Timestamp]:
    ts = pd.to_datetime(row.get("analyzed_at"), errors="coerce")
    if pd.notna(ts):
        return ts.normalize()

    src = str(row.get("_src_file", ""))
    # sentiment_summary_YYYYMMDD_HHMMSS.csv
    try:
        stamp = src.replace("sentiment_summary_", "").replace(".csv", "")
        if len(stamp) >= 8 and stamp[:8].isdigit():
            return pd.to_datetime(stamp[:8], format="%Y%m%d", errors="coerce")
    except Exception:
        pass
    return pd.NaT


def _load_summary_df(sentiment_dir: Path) -> pd.DataFrame:
    files = sorted(sentiment_dir.glob("sentiment_summary_*.csv"))
    if not files:
        return pd.DataFrame()

    parts = []
    for fp in files:
        try:
            df = pd.read_csv(fp)
        except Exception:
            continue
        if df.empty:
            continue
        df["_src_file"] = fp.name
        parts.append(df)

    if not parts:
        return pd.DataFrame()

    df = pd.concat(parts, ignore_index=True)

    analysis_date = df.apply(_analysis_date_from_row, axis=1)

    out = pd.DataFrame(
        {
            "ticker": df.get("symbol", pd.Series(dtype=str)).astype(str).str.upper().str.strip(),
            "analysis_date": pd.to_datetime(analysis_date, errors="coerce").dt.date,
            "article_count": pd.to_numeric(df.get("article_count", pd.Series(dtype=float)), errors="coerce"),
            "avg_sentiment": pd.to_numeric(df.get("average_sentiment", pd.Series(dtype=float)), errors="coerce"),
            "median_sentiment": pd.Series([float("nan")] * len(df), dtype="float64"),
            "positive_count": pd.to_numeric(df.get("positive_articles", pd.Series(dtype=float)), errors="coerce"),
            "negative_count": pd.to_numeric(df.get("negative_articles", pd.Series(dtype=float)), errors="coerce"),
            "neutral_count": pd.to_numeric(df.get("neutral_articles", pd.Series(dtype=float)), errors="coerce"),
            "sentiment_trend": df.get("sentiment_trend", pd.Series(dtype=str)).astype(str).str.strip(),
            "momentum": pd.to_numeric(df.get("momentum", pd.Series(dtype=float)), errors="coerce"),
            "confidence": pd.to_numeric(df.get("confidence", pd.Series(dtype=float)), errors="coerce"),
            "recommendation": df.get("recommendation", pd.Series(dtype=str)).astype(str).str.strip(),
        }
    )

    out = out[(out["ticker"] != "")]
    out = out.dropna(subset=["analysis_date"])
    out = out.drop_duplicates(subset=["ticker", "analysis_date"], keep="last")
    return out.reset_index(drop=True)


def main() -> int:
    sentiment_dir = Path("data/sentiment")
    if not sentiment_dir.exists():
        raise SystemExit(f"Missing sentiment directory: {sentiment_dir}")

    news_df = _load_news_df(sentiment_dir)
    summary_df = _load_summary_df(sentiment_dir)

    print(f"news_rows_prepared {len(news_df)}")
    print(f"summary_rows_prepared {len(summary_df)}")

    if news_df.empty and summary_df.empty:
        print("No sentiment rows to ingest")
        return 0

    engine = _get_engine()
    try:
        with engine.begin() as conn:
            if not news_df.empty:
                news_df.to_sql("stg_news_sentiment_import", conn, if_exists="replace", index=False)
                conn.execute(text(
                    """
                    INSERT INTO news_sentiment (
                        id, ticker, headline, source, published_at, sentiment_score,
                        sentiment_label, relevance_score, url
                    )
                    SELECT
                        m.max_id + ROW_NUMBER() OVER (
                            ORDER BY s.published_at, s.ticker, s.headline
                        ) AS id,
                        s.ticker,
                        s.headline,
                        s.source,
                        s.published_at,
                        s.sentiment_score,
                        s.sentiment_label,
                        s.relevance_score,
                        s.url
                    FROM stg_news_sentiment_import s
                    CROSS JOIN (
                        SELECT COALESCE(MAX(id), 0) AS max_id FROM news_sentiment
                    ) m
                    WHERE NOT EXISTS (
                        SELECT 1
                        FROM news_sentiment n
                        WHERE COALESCE(n.ticker, '') = COALESCE(s.ticker, '')
                          AND COALESCE(n.headline, '') = COALESCE(s.headline, '')
                          AND COALESCE(n.source, '') = COALESCE(s.source, '')
                          AND n.published_at = s.published_at
                          AND COALESCE(n.url, '') = COALESCE(s.url, '')
                    )
                    """
                ))

            if not summary_df.empty:
                summary_df.to_sql("stg_sentiment_summary_import", conn, if_exists="replace", index=False)
                conn.execute(text(
                    """
                    INSERT INTO sentiment_summary (
                        ticker, analysis_date, article_count, avg_sentiment, median_sentiment,
                        positive_count, negative_count, neutral_count, sentiment_trend,
                        momentum, confidence, recommendation
                    )
                    SELECT
                        s.ticker, s.analysis_date, s.article_count, s.avg_sentiment, s.median_sentiment,
                        s.positive_count, s.negative_count, s.neutral_count, s.sentiment_trend,
                        s.momentum, s.confidence, s.recommendation
                    FROM stg_sentiment_summary_import s
                    ON CONFLICT (ticker, analysis_date) DO UPDATE SET
                        article_count = EXCLUDED.article_count,
                        avg_sentiment = EXCLUDED.avg_sentiment,
                        median_sentiment = EXCLUDED.median_sentiment,
                        positive_count = EXCLUDED.positive_count,
                        negative_count = EXCLUDED.negative_count,
                        neutral_count = EXCLUDED.neutral_count,
                        sentiment_trend = EXCLUDED.sentiment_trend,
                        momentum = EXCLUDED.momentum,
                        confidence = EXCLUDED.confidence,
                        recommendation = EXCLUDED.recommendation
                    """
                ))

        with engine.begin() as conn:
            news_count = conn.execute(text("SELECT COUNT(*) FROM news_sentiment")).scalar()
            summary_count = conn.execute(text("SELECT COUNT(*) FROM sentiment_summary")).scalar()

        print(f"news_sentiment_total {int(news_count or 0)}")
        print(f"sentiment_summary_total {int(summary_count or 0)}")

    finally:
        engine.dispose()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
