"""
Options Metrics Calculator

Calculates and stores options chain analytics:
- Put/Call ratios (volume and open interest)
- Implied volatility aggregates (mean, skew, rank, percentile)
- Black-Scholes Greeks analytics by expiration
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Optional, List, Dict, Any
import logging

import numpy as np
import pandas as pd

from modules.database import get_db_connection

try:
    import yfinance as yf
    YF_AVAILABLE = True
except ImportError:
    YF_AVAILABLE = False

try:
    from scipy.stats import norm
    SCIPY_AVAILABLE = True
except ImportError:
    SCIPY_AVAILABLE = False


logger = logging.getLogger(__name__)


class OptionsMetricsCalculator:
    """Calculate and store options metrics for one or more tickers."""

    def __init__(self):
        self.db = get_db_connection()
        self._ensure_greeks_table()

    def _ensure_greeks_table(self) -> None:
        """Create the Greeks analytics table if it does not exist."""
        try:
            self.db.execute(
                """
                CREATE TABLE IF NOT EXISTS options_greeks_analytics (
                    ticker VARCHAR NOT NULL,
                    date DATE NOT NULL,
                    expiration_date DATE NOT NULL,
                    underlying_price FLOAT,
                    avg_iv FLOAT,
                    call_contracts BIGINT,
                    put_contracts BIGINT,
                    call_delta_mean FLOAT,
                    put_delta_mean FLOAT,
                    gamma_mean FLOAT,
                    theta_mean FLOAT,
                    vega_mean FLOAT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (ticker, date, expiration_date)
                )
                """
            )
        except Exception as exc:
            logger.warning("Could not ensure options_greeks_analytics table: %s", exc)

    @staticmethod
    def _safe_div(num: float, den: float) -> Optional[float]:
        if den is None or den == 0:
            return None
        return float(num / den)

    @staticmethod
    def _to_expiration_date(expiration: str) -> date:
        return datetime.strptime(expiration, "%Y-%m-%d").date()

    @staticmethod
    def _time_to_expiration(expiration: str, as_of: datetime) -> float:
        exp_dt = datetime.strptime(expiration, "%Y-%m-%d")
        days = max((exp_dt - as_of).days, 1)
        return float(days / 365.0)

    def _calculate_greeks_vectorized(
        self,
        df: pd.DataFrame,
        risk_free_rate: float = 0.045,
    ) -> pd.DataFrame:
        """Calculate Delta/Gamma/Theta/Vega in bulk using Black-Scholes."""
        out = df.copy()
        out["delta"] = np.nan
        out["gamma"] = np.nan
        out["theta"] = np.nan
        out["vega"] = np.nan

        if out.empty or not SCIPY_AVAILABLE:
            return out

        required = [
            "underlying_price",
            "strike",
            "time_to_expiration",
            "impliedVolatility",
            "option_type",
        ]
        for col in required:
            if col not in out.columns:
                return out

        S = pd.to_numeric(out["underlying_price"], errors="coerce")
        K = pd.to_numeric(out["strike"], errors="coerce")
        T = pd.to_numeric(out["time_to_expiration"], errors="coerce")
        sigma = pd.to_numeric(out["impliedVolatility"], errors="coerce")

        valid = (S > 0) & (K > 0) & (T > 0) & (sigma > 0)
        if not valid.any():
            return out

        S_v = S[valid].to_numpy(dtype=float)
        K_v = K[valid].to_numpy(dtype=float)
        T_v = T[valid].to_numpy(dtype=float)
        sigma_v = sigma[valid].to_numpy(dtype=float)

        d1 = (np.log(S_v / K_v) + (risk_free_rate + 0.5 * sigma_v ** 2) * T_v) / (sigma_v * np.sqrt(T_v))
        d2 = d1 - sigma_v * np.sqrt(T_v)

        pdf_d1 = norm.pdf(d1)
        cdf_d1 = norm.cdf(d1)
        cdf_d2 = norm.cdf(d2)

        gamma = pdf_d1 / (S_v * sigma_v * np.sqrt(T_v))
        vega = S_v * np.sqrt(T_v) * pdf_d1 / 100.0

        option_types = out.loc[valid, "option_type"].str.lower().to_numpy()
        call_mask = option_types == "call"

        delta = np.full_like(cdf_d1, np.nan)
        theta = np.full_like(cdf_d1, np.nan)

        delta[call_mask] = cdf_d1[call_mask]
        theta[call_mask] = (
            -((S_v[call_mask] * pdf_d1[call_mask] * sigma_v[call_mask]) / (2 * np.sqrt(T_v[call_mask])))
            - risk_free_rate * K_v[call_mask] * np.exp(-risk_free_rate * T_v[call_mask]) * cdf_d2[call_mask]
        ) / 365.0

        put_mask = ~call_mask
        delta[put_mask] = cdf_d1[put_mask] - 1.0
        theta[put_mask] = (
            -((S_v[put_mask] * pdf_d1[put_mask] * sigma_v[put_mask]) / (2 * np.sqrt(T_v[put_mask])))
            + risk_free_rate * K_v[put_mask] * np.exp(-risk_free_rate * T_v[put_mask]) * norm.cdf(-d2[put_mask])
        ) / 365.0

        out.loc[valid, "delta"] = delta
        out.loc[valid, "gamma"] = gamma
        out.loc[valid, "theta"] = theta
        out.loc[valid, "vega"] = vega

        return out

    def _fetch_one_ticker_chain(
        self,
        ticker: str,
        max_expirations: Optional[int] = None,
    ) -> pd.DataFrame:
        """Fetch full options chain rows for a ticker across expirations."""
        if not YF_AVAILABLE:
            return pd.DataFrame()

        stock = yf.Ticker(ticker)
        history = stock.history(period="1d")
        if history.empty:
            logger.warning("No price data for ticker %s", ticker)
            return pd.DataFrame()

        underlying_price = float(history["Close"].iloc[-1])
        as_of = datetime.utcnow()

        expirations = list(stock.options or [])
        if not expirations:
            return pd.DataFrame()
        if max_expirations and max_expirations > 0:
            expirations = expirations[:max_expirations]

        frames: List[pd.DataFrame] = []
        for exp in expirations:
            try:
                chain = stock.option_chain(exp)
                calls = chain.calls.copy()
                puts = chain.puts.copy()

                calls["option_type"] = "call"
                puts["option_type"] = "put"

                merged = pd.concat([calls, puts], ignore_index=True)
                if merged.empty:
                    continue

                merged["ticker"] = ticker
                merged["date"] = as_of.date()
                merged["expiration_date"] = self._to_expiration_date(exp)
                merged["underlying_price"] = underlying_price
                merged["time_to_expiration"] = self._time_to_expiration(exp, as_of)

                frames.append(merged)
            except Exception as exc:
                logger.warning("Error processing %s expiration %s: %s", ticker, exp, exc)

        if not frames:
            return pd.DataFrame()

        raw = pd.concat(frames, ignore_index=True)
        return self._calculate_greeks_vectorized(raw)

    def _iv_rank_and_percentile(
        self,
        ticker: str,
        current_iv: Optional[float],
        lookback_days: int = 252,
    ) -> tuple[Optional[float], Optional[float]]:
        """Calculate IV rank and percentile from historical options_data."""
        if current_iv is None or np.isnan(current_iv):
            return None, None

        cutoff = (datetime.utcnow().date() - timedelta(days=lookback_days)).isoformat()
        sql = """
            SELECT (total_put_iv + total_call_iv) / 2.0 AS avg_iv
            FROM options_data
            WHERE ticker = ? AND date >= ?
              AND total_put_iv IS NOT NULL
              AND total_call_iv IS NOT NULL
        """

        try:
            hist = self.db.query(sql, (ticker, cutoff))
        except Exception as exc:
            logger.warning("IV history query failed for %s: %s", ticker, exc)
            return None, None

        if hist.empty:
            return None, None

        series = pd.to_numeric(hist["avg_iv"], errors="coerce").dropna()
        if series.empty:
            return None, None

        min_iv = float(series.min())
        max_iv = float(series.max())

        if max_iv == min_iv:
            iv_rank = 50.0
        else:
            iv_rank = float(((current_iv - min_iv) / (max_iv - min_iv)) * 100.0)
            iv_rank = float(np.clip(iv_rank, 0.0, 100.0))

        iv_percentile = float((series < current_iv).mean() * 100.0)
        return iv_rank, iv_percentile

    def _build_expiration_metrics(self, chain_df: pd.DataFrame) -> pd.DataFrame:
        """Aggregate row-level chain into per-expiration options_data records."""
        if chain_df.empty:
            return pd.DataFrame()

        records: List[Dict[str, Any]] = []

        for (ticker, as_of_date, expiration), grp in chain_df.groupby(["ticker", "date", "expiration_date"], as_index=False):
            calls = grp[grp["option_type"] == "call"]
            puts = grp[grp["option_type"] == "put"]

            call_volume = int(pd.to_numeric(calls.get("volume"), errors="coerce").fillna(0).sum())
            put_volume = int(pd.to_numeric(puts.get("volume"), errors="coerce").fillna(0).sum())
            call_oi = int(pd.to_numeric(calls.get("openInterest"), errors="coerce").fillna(0).sum())
            put_oi = int(pd.to_numeric(puts.get("openInterest"), errors="coerce").fillna(0).sum())

            call_iv_mean = pd.to_numeric(calls.get("impliedVolatility"), errors="coerce").dropna()
            put_iv_mean = pd.to_numeric(puts.get("impliedVolatility"), errors="coerce").dropna()
            total_call_iv = float(call_iv_mean.mean()) if not call_iv_mean.empty else None
            total_put_iv = float(put_iv_mean.mean()) if not put_iv_mean.empty else None

            avg_iv = None
            if total_call_iv is not None and total_put_iv is not None:
                avg_iv = float((total_call_iv + total_put_iv) / 2.0)

            iv_rank, iv_percentile = self._iv_rank_and_percentile(ticker, avg_iv)

            records.append(
                {
                    "ticker": ticker,
                    "date": as_of_date,
                    "expiration_date": expiration,
                    "put_volume": put_volume,
                    "call_volume": call_volume,
                    "put_open_interest": put_oi,
                    "call_open_interest": call_oi,
                    "put_call_volume_ratio": self._safe_div(put_volume, call_volume),
                    "put_call_oi_ratio": self._safe_div(put_oi, call_oi),
                    "total_put_iv": total_put_iv,
                    "total_call_iv": total_call_iv,
                    "iv_rank": iv_rank,
                    "iv_percentile": iv_percentile,
                    "skew": (total_put_iv - total_call_iv) if (total_put_iv is not None and total_call_iv is not None) else None,
                }
            )

        return pd.DataFrame(records)

    def _build_greeks_analytics(self, chain_df: pd.DataFrame) -> pd.DataFrame:
        """Build per-expiration Greeks analytics records."""
        if chain_df.empty:
            return pd.DataFrame()

        records: List[Dict[str, Any]] = []
        for (ticker, as_of_date, expiration), grp in chain_df.groupby(["ticker", "date", "expiration_date"], as_index=False):
            calls = grp[grp["option_type"] == "call"]
            puts = grp[grp["option_type"] == "put"]

            avg_iv_series = pd.to_numeric(grp.get("impliedVolatility"), errors="coerce").dropna()
            avg_iv = float(avg_iv_series.mean()) if not avg_iv_series.empty else None

            records.append(
                {
                    "ticker": ticker,
                    "date": as_of_date,
                    "expiration_date": expiration,
                    "underlying_price": float(pd.to_numeric(grp["underlying_price"], errors="coerce").dropna().iloc[0]) if not grp.empty else None,
                    "avg_iv": avg_iv,
                    "call_contracts": int(len(calls)),
                    "put_contracts": int(len(puts)),
                    "call_delta_mean": float(pd.to_numeric(calls.get("delta"), errors="coerce").mean()) if not calls.empty else None,
                    "put_delta_mean": float(pd.to_numeric(puts.get("delta"), errors="coerce").mean()) if not puts.empty else None,
                    "gamma_mean": float(pd.to_numeric(grp.get("gamma"), errors="coerce").mean()) if not grp.empty else None,
                    "theta_mean": float(pd.to_numeric(grp.get("theta"), errors="coerce").mean()) if not grp.empty else None,
                    "vega_mean": float(pd.to_numeric(grp.get("vega"), errors="coerce").mean()) if not grp.empty else None,
                }
            )

        return pd.DataFrame(records)

    def fetch_options_data(self, ticker: str, date: Optional[str] = None) -> dict:
        """
        Fetch options metrics for API usage.

        Returns nearest-expiration metrics if available.
        """
        chain_df = self._fetch_one_ticker_chain(ticker=ticker, max_expirations=1)
        if chain_df.empty:
            return {}

        metrics_df = self._build_expiration_metrics(chain_df)
        if metrics_df.empty:
            return {}

        row = metrics_df.iloc[0].to_dict()
        if date:
            row["date"] = date
        return row

    def calculate_options_features(self, ticker: str, date: Optional[str] = None) -> pd.DataFrame:
        """Calculate per-expiration options features for a single ticker."""
        chain_df = self._fetch_one_ticker_chain(ticker=ticker)
        if chain_df.empty:
            return pd.DataFrame()

        metrics_df = self._build_expiration_metrics(chain_df)
        if date and not metrics_df.empty:
            metrics_df["date"] = pd.to_datetime(date).date()

        return metrics_df

    def store_options_data(self, df: pd.DataFrame) -> None:
        """Store options expiration metrics in options_data."""
        if df.empty:
            return

        cols = [
            "ticker",
            "date",
            "expiration_date",
            "put_volume",
            "call_volume",
            "put_open_interest",
            "call_open_interest",
            "put_call_volume_ratio",
            "put_call_oi_ratio",
            "total_put_iv",
            "total_call_iv",
            "iv_rank",
            "iv_percentile",
            "skew",
        ]
        payload = df[[c for c in cols if c in df.columns]].copy()

        self.db.insert_df(
            payload,
            "options_data",
            conflict_columns=["ticker", "date", "expiration_date"],
        )

    def store_greeks_analytics(self, df: pd.DataFrame) -> None:
        """Store per-expiration Greeks analytics in options_greeks_analytics."""
        if df.empty:
            return

        self.db.insert_df(
            df,
            "options_greeks_analytics",
            conflict_columns=["ticker", "date", "expiration_date"],
        )

    def calculate_and_store(self, ticker: str, date: Optional[str] = None) -> pd.DataFrame:
        """Calculate and store options and Greeks analytics for one ticker."""
        chain_df = self._fetch_one_ticker_chain(ticker=ticker)
        if chain_df.empty:
            return pd.DataFrame()

        metrics_df = self._build_expiration_metrics(chain_df)
        greeks_df = self._build_greeks_analytics(chain_df)

        if date:
            as_of = pd.to_datetime(date).date()
            metrics_df["date"] = as_of
            greeks_df["date"] = as_of

        if not metrics_df.empty:
            self.store_options_data(metrics_df)
        if not greeks_df.empty:
            self.store_greeks_analytics(greeks_df)

        return metrics_df

    def batch_calculate(
        self,
        tickers: List[str],
        date: Optional[str] = None,
        max_expirations: Optional[int] = None,
    ) -> Dict[str, pd.DataFrame]:
        """Calculate and store options metrics for multiple tickers."""
        results: Dict[str, pd.DataFrame] = {}

        for ticker in tickers:
            try:
                chain_df = self._fetch_one_ticker_chain(ticker=ticker, max_expirations=max_expirations)
                if chain_df.empty:
                    results[ticker] = pd.DataFrame()
                    logger.warning("No options chain for %s", ticker)
                    continue

                metrics_df = self._build_expiration_metrics(chain_df)
                greeks_df = self._build_greeks_analytics(chain_df)

                if date:
                    as_of = pd.to_datetime(date).date()
                    metrics_df["date"] = as_of
                    greeks_df["date"] = as_of

                self.store_options_data(metrics_df)
                self.store_greeks_analytics(greeks_df)
                results[ticker] = metrics_df
                logger.info("Stored options metrics for %s (%s expirations)", ticker, len(metrics_df))
            except Exception as exc:
                logger.error("Error calculating options metrics for %s: %s", ticker, exc)
                results[ticker] = pd.DataFrame()

        return results

    def get_historical_put_call_ratio(
        self,
        ticker: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> pd.DataFrame:
        """Get historical put/call ratio metrics from options_data."""
        sql = """
            SELECT date,
                   ticker,
                   expiration_date,
                   put_call_volume_ratio,
                   put_call_oi_ratio,
                   iv_rank,
                   iv_percentile,
                   skew
            FROM options_data
            WHERE ticker = ?
        """

        params: List[Any] = [ticker]
        if start_date:
            sql += " AND date >= ?"
            params.append(start_date)
        if end_date:
            sql += " AND date <= ?"
            params.append(end_date)

        sql += " ORDER BY date, expiration_date"
        return self.db.query(sql, tuple(params))
