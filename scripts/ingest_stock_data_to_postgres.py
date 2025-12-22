"""Ingest local stock/ETF OHLCV CSVs into PostgreSQL.

This script is intended for bulk-loading a folder of per-ticker CSV files (e.g. Yahoo Finance
format) into the project's `yfinance_ohlcv` table.

It performs an idempotent upsert on (ticker, date).

Usage (PowerShell):
  $env:DATABASE_BACKEND='postgresql'
  $env:POSTGRES_HOST='localhost'
  $env:POSTGRES_PORT='5432'
  $env:POSTGRES_DB='economic_dashboard'
  $env:POSTGRES_USER='dashboard_user'
  $env:POSTGRES_PASSWORD='dashboard_pass'
  C:/Users/Moshe/PycharmProjects/Economic-Dashboard-API/.venv/Scripts/python.exe scripts/ingest_stock_data_to_postgres.py --data-dir "C:\\Users\\Moshe\\Downloads\\stock_data"
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from typing import Iterable, Optional

import pandas as pd


# Allow running as a script from the repo root (like other scripts/ utilities).
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


RESERVED_DEVICE_NAMES = {
    "CON",
    "PRN",
    "AUX",
    "NUL",
    *{f"COM{i}" for i in range(1, 10)},
    *{f"LPT{i}" for i in range(1, 10)},
}


def _normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    # Normalize common Yahoo Finance column variants.
    rename_map = {}
    for col in df.columns:
        key = str(col).strip().lower().replace(" ", "_")
        if key in {"date", "datetime"}:
            rename_map[col] = "date"
        elif key in {"open"}:
            rename_map[col] = "open"
        elif key in {"high"}:
            rename_map[col] = "high"
        elif key in {"low"}:
            rename_map[col] = "low"
        elif key in {"close"}:
            rename_map[col] = "close"
        elif key in {"adj_close", "adjclose", "adj_close_"}:
            rename_map[col] = "adj_close"
        elif key in {"volume", "vol"}:
            rename_map[col] = "volume"

    df = df.rename(columns=rename_map)
    return df


def _extract_ticker_from_path(csv_path: Path) -> str:
    # Use filename stem as ticker; tolerate Windows reserved device names.
    stem = csv_path.stem.strip()
    ticker = stem.upper()
    # Some datasets may include reserved device names (e.g. PRN.csv). That is still a valid ticker.
    # Keep it as-is.
    return ticker


def _load_csv_to_ohlcv_df(csv_path: Path, ticker: str) -> pd.DataFrame:
    df = pd.read_csv(csv_path)
    df = _normalize_columns(df)

    if "date" not in df.columns:
        raise ValueError(f"{csv_path}: missing 'Date'/'date' column")

    required_price_cols = {"open", "high", "low", "close"}
    missing_prices = sorted(required_price_cols - set(df.columns))
    if missing_prices:
        raise ValueError(f"{csv_path}: missing columns: {missing_prices}")

    if "adj_close" not in df.columns:
        df["adj_close"] = df["close"]
    if "volume" not in df.columns:
        df["volume"] = pd.NA

    out = pd.DataFrame(
        {
            "ticker": ticker,
            "date": pd.to_datetime(df["date"], errors="coerce").dt.date,
            "open": pd.to_numeric(df["open"], errors="coerce"),
            "high": pd.to_numeric(df["high"], errors="coerce"),
            "low": pd.to_numeric(df["low"], errors="coerce"),
            "close": pd.to_numeric(df["close"], errors="coerce"),
            "volume": pd.to_numeric(df["volume"], errors="coerce").astype("Int64"),
            "adj_close": pd.to_numeric(df["adj_close"], errors="coerce"),
        }
    )

    out = out.dropna(subset=["date"])
    out = out.drop_duplicates(subset=["ticker", "date"], keep="last")
    out = out.sort_values(["ticker", "date"], ascending=[True, True])

    return out


def _iter_csv_files(data_dir: Path) -> Iterable[Path]:
    # All CSVs, recursively.
    yield from data_dir.rglob("*.csv")


def _get_postgres_connection_url(explicit_url: Optional[str] = None) -> str:
    if explicit_url:
        return explicit_url

    # Ensure we use the project's backend config logic.
    os.environ.setdefault("DATABASE_BACKEND", "postgresql")

    from modules.database.factory import get_backend

    backend = get_backend()
    backend_name = backend.__class__.__name__
    if backend_name != "PostgreSQLBackend":
        raise RuntimeError(
            f"Expected PostgreSQL backend, got {backend_name}. "
            "Set DATABASE_BACKEND=postgresql and configure POSTGRES_* or DATABASE_URL."
        )

    if not hasattr(backend, "connection_url"):
        raise RuntimeError("PostgreSQL backend missing connection_url")

    return str(getattr(backend, "connection_url"))


def _upsert_yfinance_ohlcv(engine, ohlcv_table, df: pd.DataFrame, chunk_size: int) -> int:
    if df.empty:
        return 0

    from sqlalchemy.dialects.postgresql import insert

    records = df.to_dict(orient="records")
    affected = 0

    with engine.begin() as conn:
        for start in range(0, len(records), chunk_size):
            chunk = records[start : start + chunk_size]
            stmt = insert(ohlcv_table).values(chunk)
            stmt = stmt.on_conflict_do_update(
                index_elements=["ticker", "date"],
                set_={
                    "open": stmt.excluded.open,
                    "high": stmt.excluded.high,
                    "low": stmt.excluded.low,
                    "close": stmt.excluded.close,
                    "volume": stmt.excluded.volume,
                    "adj_close": stmt.excluded.adj_close,
                },
            )
            result = conn.execute(stmt)
            # Postgres returns number of rows "affected" (inserted + updated).
            affected += int(result.rowcount or 0)

    return affected


def main() -> int:
    parser = argparse.ArgumentParser(description="Ingest local OHLCV CSVs into PostgreSQL yfinance_ohlcv")
    parser.add_argument("--data-dir", required=True, help="Root folder containing per-ticker CSVs")
    parser.add_argument(
        "--connection-url",
        default=None,
        help="Optional SQLAlchemy PostgreSQL URL. If omitted, uses POSTGRES_* env vars / DATABASE_URL.",
    )
    parser.add_argument(
        "--tickers",
        default=None,
        help="Optional comma-separated list of tickers to ingest (matches filename stems)",
    )
    parser.add_argument(
        "--limit-files",
        type=int,
        default=None,
        help="Optional limit on number of CSV files to process (for debugging)",
    )
    parser.add_argument("--dry-run", action="store_true", help="Parse and report counts, but do not write to DB")
    parser.add_argument("--chunk-size", type=int, default=2000, help="Upsert batch size")
    parser.add_argument(
        "--log-every",
        type=int,
        default=50,
        help="Progress log frequency in number of processed files (ignored with --verbose)",
    )
    parser.add_argument("--verbose", action="store_true", help="Print one line per ingested file")

    args = parser.parse_args()

    data_dir = Path(args.data_dir).expanduser().resolve()
    if not data_dir.exists() or not data_dir.is_dir():
        raise SystemExit(f"data-dir not found or not a directory: {data_dir}")

    ticker_filter = None
    if args.tickers:
        ticker_filter = {t.strip().upper() for t in args.tickers.split(",") if t.strip()}

    csv_files = []
    for p in _iter_csv_files(data_dir):
        ticker = _extract_ticker_from_path(p)
        if ticker_filter and ticker not in ticker_filter:
            continue
        csv_files.append(p)
        if args.limit_files and len(csv_files) >= args.limit_files:
            break

    if not csv_files:
        print(f"No CSV files found under: {data_dir}")
        return 1

    connection_url = None if args.dry_run else _get_postgres_connection_url(args.connection_url)

    engine = None
    ohlcv_table = None
    if not args.dry_run:
        from sqlalchemy import BigInteger, Column, Date, Float, MetaData, String, Table, create_engine

        engine = create_engine(connection_url)
        metadata = MetaData()
        ohlcv_table = Table(
            "yfinance_ohlcv",
            metadata,
            Column("ticker", String(20), primary_key=True),
            Column("date", Date, primary_key=True),
            Column("open", Float),
            Column("high", Float),
            Column("low", Float),
            Column("close", Float),
            Column("volume", BigInteger),
            Column("adj_close", Float),
        )

    total_files = 0
    total_rows = 0
    total_affected = 0
    total_skipped = 0

    total_planned = len(csv_files)

    for csv_path in csv_files:
        ticker = _extract_ticker_from_path(csv_path)
        try:
            df = _load_csv_to_ohlcv_df(csv_path, ticker)
        except Exception as exc:
            total_skipped += 1
            if args.verbose or args.dry_run:
                print(f"SKIP {csv_path}: {exc}")
            continue

        total_files += 1
        total_rows += len(df)

        if args.dry_run:
            min_date = df["date"].min() if not df.empty else None
            max_date = df["date"].max() if not df.empty else None
            print(f"OK   {ticker:<8} rows={len(df):>7} range={min_date}..{max_date} file={csv_path}")
            continue

        affected = _upsert_yfinance_ohlcv(engine, ohlcv_table, df, chunk_size=args.chunk_size)
        total_affected += affected
        if args.verbose:
            print(f"UPSERT {ticker:<8} rows={len(df):>7} affected={affected:>7} file={csv_path}")
        elif args.log_every and (total_files % args.log_every == 0 or total_files == total_planned):
            print(
                f"PROGRESS files={total_files}/{total_planned} skipped={total_skipped} "
                f"rows={total_rows} affected={total_affected}"
            )

    print("-")
    print(f"Processed files: {total_files}")
    print(f"Skipped files:   {total_skipped}")
    print(f"Parsed rows:     {total_rows}")
    if not args.dry_run:
        print(f"DB affected:     {total_affected}")

    if engine is not None:
        engine.dispose()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
