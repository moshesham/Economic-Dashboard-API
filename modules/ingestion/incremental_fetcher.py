"""
Incremental Data Fetcher
========================
Tracks per-series high-water marks in ``data_ingestion_watermarks`` so that
every refresh cycle only pulls *new* records rather than re-fetching full
history.

Usage example
-------------
    from modules.ingestion import IncrementalFetcher

    fetcher = IncrementalFetcher()

    # Fetch FRED series - only data newer than the stored watermark
    df = fetcher.fetch_fred_incremental("UNRATE")

    # Fetch a batch of series
    dfs = fetcher.fetch_fred_batch_incremental(
        {"Unemployment Rate": "UNRATE", "CPI": "CPIAUCSL"},
        default_start_date="2000-01-01",
    )

    # Fetch Yahoo Finance OHLCV
    ohlcv = fetcher.fetch_yfinance_incremental("^GSPC", period_fallback="20y")
"""

from __future__ import annotations

import logging
import time
from datetime import date, datetime, timedelta
from typing import Dict, Optional

import pandas as pd

logger = logging.getLogger(__name__)

# Seconds to wait between API requests to respect rate limits
_RATE_LIMIT_DELAY = 0.5

# Default look-back when no watermark exists yet for a series
_DEFAULT_HISTORY_YEARS = 20


class IncrementalFetcher:
    """
    Wraps data-source clients with incremental-load logic backed by the
    ``data_ingestion_watermarks`` database table.

    The fetcher:
    1. Reads the stored high-water mark for a (source, series_key) pair.
    2. Calls the upstream API asking only for data *after* that date.
    3. Upserts the new rows into the main data tables.
    4. Updates the watermark so the next run starts from the new frontier.

    If no watermark exists (first run), it falls back to fetching full
    history going back ``_DEFAULT_HISTORY_YEARS`` years.
    """

    def __init__(self):
        self._db = None  # lazy-initialised to avoid import-time side-effects

    # ------------------------------------------------------------------
    # Database helpers
    # ------------------------------------------------------------------

    def _get_db(self):
        if self._db is None:
            try:
                from modules.database.factory import get_database_backend
                self._db = get_database_backend()
            except Exception as exc:
                logger.warning("Database backend unavailable: %s", exc)
        return self._db

    def get_watermark(self, source: str, series_key: str) -> Optional[date]:
        """Return the last successfully-fetched date for this series, or None."""
        db = self._get_db()
        if db is None:
            return None
        try:
            df = db.query(
                "SELECT last_fetched_date FROM data_ingestion_watermarks "
                "WHERE source = ? AND series_key = ? AND status = 'ok'",
                (source, series_key),
            )
            if not df.empty:
                val = df.iloc[0, 0]
                if isinstance(val, date):
                    return val
                return pd.to_datetime(val).date()
        except Exception as exc:
            logger.warning("Could not read watermark for %s/%s: %s", source, series_key, exc)
        return None

    def set_watermark(
        self,
        source: str,
        series_key: str,
        last_fetched_date: date,
        records_fetched: int = 0,
        status: str = "ok",
        error_message: Optional[str] = None,
    ) -> None:
        """Upsert the high-water mark for this series."""
        db = self._get_db()
        if db is None:
            return
        try:
            row = pd.DataFrame([{
                "source": source,
                "series_key": series_key,
                "last_fetched_date": last_fetched_date,
                "last_run_at": datetime.utcnow(),
                "records_fetched": records_fetched,
                "status": status,
                "error_message": error_message,
            }])
            db.insert_df(
                row,
                table_name="data_ingestion_watermarks",
                if_exists="append",
                conflict_columns=["source", "series_key"],
            )
        except Exception as exc:
            logger.warning("Could not write watermark for %s/%s: %s", source, series_key, exc)

    # ------------------------------------------------------------------
    # FRED incremental helpers
    # ------------------------------------------------------------------

    def fetch_fred_incremental(
        self,
        series_id: str,
        default_start_date: str = "2000-01-01",
        api_key: Optional[str] = None,
    ) -> pd.DataFrame:
        """
        Fetch a single FRED series, starting from the day *after* the stored
        watermark (or ``default_start_date`` if no watermark exists yet).

        Returns a DataFrame with a DatetimeIndex and a column named
        ``series_id``.  Returns an empty DataFrame on failure.
        """
        from pandas_datareader import data as pdr

        watermark = self.get_watermark("fred", series_id)
        if watermark is not None:
            start = watermark + timedelta(days=1)
        else:
            start = pd.to_datetime(default_start_date).date()

        end = date.today()

        if start > end:
            logger.debug("FRED/%s is already up-to-date (watermark=%s)", series_id, watermark)
            return pd.DataFrame()

        logger.info("FRED/%s: fetching %s → %s", series_id, start, end)
        try:
            kwargs = {"api_key": api_key} if api_key else {}
            df = pdr.DataReader(series_id, "fred", start=str(start), end=str(end), **kwargs)
            if df.empty:
                return pd.DataFrame()

            df = df.rename(columns={series_id: series_id})

            # Persist into fred_data table
            db = self._get_db()
            if db is not None:
                rows = df.reset_index().rename(columns={"DATE": "date", series_id: "value"})
                rows["series_id"] = series_id
                rows = rows[["series_id", "date", "value"]]
                db.insert_df(
                    rows,
                    table_name="fred_data",
                    if_exists="append",
                    conflict_columns=["series_id", "date"],
                )

            new_max = df.index.max().date()
            self.set_watermark("fred", series_id, new_max, records_fetched=len(df))
            return df

        except Exception as exc:
            self.set_watermark(
                "fred", series_id, end, status="error", error_message=str(exc)[:500]
            )
            logger.error("Failed to fetch FRED/%s: %s", series_id, exc)
            return pd.DataFrame()

    def fetch_fred_batch_incremental(
        self,
        series_dict: Dict[str, str],
        default_start_date: str = "2000-01-01",
        api_key: Optional[str] = None,
        rate_limit_delay: float = _RATE_LIMIT_DELAY,
    ) -> pd.DataFrame:
        """
        Incrementally fetch multiple FRED series in a single call.

        ``series_dict`` maps descriptive label → FRED series ID, e.g.::

            {"Unemployment Rate": "UNRATE", "CPI": "CPIAUCSL"}

        Returns a combined DataFrame with one column per label (matching the
        keys in ``series_dict``), indexed by date.  Only columns where new
        data was fetched are included; existing data is **not** re-fetched.
        """
        frames: Dict[str, pd.Series] = {}
        for label, series_id in series_dict.items():
            df = self.fetch_fred_incremental(
                series_id, default_start_date=default_start_date, api_key=api_key
            )
            if not df.empty:
                frames[label] = df.iloc[:, 0]
            time.sleep(rate_limit_delay)

        if not frames:
            return pd.DataFrame()
        return pd.DataFrame(frames)

    # ------------------------------------------------------------------
    # Yahoo Finance incremental helpers
    # ------------------------------------------------------------------

    def fetch_yfinance_incremental(
        self,
        ticker: str,
        period_fallback: str = "20y",
        interval: str = "1d",
    ) -> pd.DataFrame:
        """
        Fetch Yahoo Finance OHLCV for *ticker*, starting from the day after
        the stored watermark.

        When there is no watermark the full ``period_fallback`` is fetched.
        Returns a standard OHLCV DataFrame (empty on failure).
        """
        import yfinance as yf

        watermark = self.get_watermark("yfinance", ticker)

        try:
            if watermark is not None:
                start = watermark + timedelta(days=1)
                end = date.today()
                if start > end:
                    logger.debug("yfinance/%s is up-to-date (watermark=%s)", ticker, watermark)
                    return pd.DataFrame()
                hist = yf.download(
                    ticker,
                    start=str(start),
                    end=str(end),
                    interval=interval,
                    progress=False,
                    auto_adjust=True,
                )
            else:
                hist = yf.download(
                    ticker,
                    period=period_fallback,
                    interval=interval,
                    progress=False,
                    auto_adjust=True,
                )

            if hist.empty:
                return pd.DataFrame()

            # Flatten MultiIndex columns that yfinance sometimes produces
            if isinstance(hist.columns, pd.MultiIndex):
                hist.columns = hist.columns.get_level_values(0)

            hist.index = pd.to_datetime(hist.index).normalize()

            # Persist into yfinance_ohlcv
            db = self._get_db()
            if db is not None:
                rows = hist.reset_index().rename(columns={"Date": "date", "index": "date"})
                rows["ticker"] = ticker
                col_map = {"Open": "open", "High": "high", "Low": "low",
                           "Close": "close", "Volume": "volume", "Adj Close": "adj_close"}
                rows = rows.rename(columns=col_map)
                keep = [c for c in ["ticker", "date", "open", "high", "low",
                                    "close", "volume", "adj_close"] if c in rows.columns]
                db.insert_df(
                    rows[keep],
                    table_name="yfinance_ohlcv",
                    if_exists="append",
                    conflict_columns=["ticker", "date"],
                )

            new_max = hist.index.max().date() if hasattr(hist.index.max(), "date") else date.today()
            self.set_watermark("yfinance", ticker, new_max, records_fetched=len(hist))
            return hist

        except Exception as exc:
            self.set_watermark(
                "yfinance", ticker, date.today(), status="error", error_message=str(exc)[:500]
            )
            logger.error("Failed to fetch yfinance/%s: %s", ticker, exc)
            return pd.DataFrame()

    def fetch_yfinance_batch_incremental(
        self,
        tickers_dict: Dict[str, str],
        period_fallback: str = "20y",
        interval: str = "1d",
        rate_limit_delay: float = _RATE_LIMIT_DELAY,
    ) -> Dict[str, pd.DataFrame]:
        """
        Incrementally fetch multiple Yahoo Finance tickers.

        ``tickers_dict`` maps descriptive label → ticker symbol.
        Returns ``{label: ohlcv_df}``.
        """
        result: Dict[str, pd.DataFrame] = {}
        for label, ticker in tickers_dict.items():
            df = self.fetch_yfinance_incremental(
                ticker, period_fallback=period_fallback, interval=interval
            )
            if not df.empty:
                result[label] = df
            time.sleep(rate_limit_delay)
        return result

    # ------------------------------------------------------------------
    # Status / reporting
    # ------------------------------------------------------------------

    def get_all_watermarks(self) -> pd.DataFrame:
        """Return a DataFrame of all current watermarks (for monitoring/UI)."""
        db = self._get_db()
        if db is None:
            return pd.DataFrame()
        try:
            return db.query(
                "SELECT source, series_key, last_fetched_date, last_run_at, "
                "records_fetched, status FROM data_ingestion_watermarks "
                "ORDER BY source, series_key"
            )
        except Exception as exc:
            logger.warning("Could not fetch watermarks: %s", exc)
            return pd.DataFrame()

    def get_stale_series(self, max_age_days: int = 1) -> pd.DataFrame:
        """Return watermark rows where last_fetched_date is older than ``max_age_days``."""
        all_wm = self.get_all_watermarks()
        if all_wm.empty:
            return all_wm
        cutoff = date.today() - timedelta(days=max_age_days)
        all_wm["last_fetched_date"] = pd.to_datetime(all_wm["last_fetched_date"]).dt.date
        return all_wm[all_wm["last_fetched_date"] < cutoff].reset_index(drop=True)


# Convenience singleton accessor
_fetcher_instance: Optional[IncrementalFetcher] = None


def get_incremental_fetcher() -> IncrementalFetcher:
    """Return a module-level shared IncrementalFetcher instance."""
    global _fetcher_instance
    if _fetcher_instance is None:
        _fetcher_instance = IncrementalFetcher()
    return _fetcher_instance
