"""Crypto market data loader (CoinGecko) with offline fallback support."""

from __future__ import annotations

from datetime import datetime
from typing import Dict
import logging

import pandas as pd
import requests

logger = logging.getLogger(__name__)

COINGECKO_MARKET_CHART = "https://api.coingecko.com/api/v3/coins/{coin_id}/market_chart"


def _fetch_market_chart(coin_id: str, days: int = 365, vs_currency: str = "usd") -> pd.DataFrame:
    """Fetch historical close/volume from CoinGecko market_chart endpoint."""
    try:
        resp = requests.get(
            COINGECKO_MARKET_CHART.format(coin_id=coin_id),
            params={"vs_currency": vs_currency, "days": days, "interval": "daily"},
            timeout=30,
        )
        resp.raise_for_status()
        payload = resp.json()
    except Exception as exc:
        logger.warning("CoinGecko fetch failed for %s: %s", coin_id, exc)
        return pd.DataFrame()

    prices = payload.get("prices", [])
    volumes = payload.get("total_volumes", [])
    if not prices:
        return pd.DataFrame()

    price_df = pd.DataFrame(prices, columns=["ts", "Close"])
    volume_df = pd.DataFrame(volumes, columns=["ts", "Volume"])
    merged = price_df.merge(volume_df, on="ts", how="left")

    merged["date"] = pd.to_datetime(merged["ts"], unit="ms").dt.normalize()
    merged = merged.set_index("date")[["Close", "Volume"]]
    merged = merged[~merged.index.duplicated(keep="last")]
    return merged.sort_index()


def fetch_crypto_batch(assets: Dict[str, str], days: int = 365, vs_currency: str = "usd") -> Dict[str, pd.DataFrame]:
    """Fetch crypto close/volume series for a mapping of label -> CoinGecko id."""
    result: Dict[str, pd.DataFrame] = {}
    for label, coin_id in assets.items():
        result[label] = _fetch_market_chart(coin_id=coin_id, days=days, vs_currency=vs_currency)
    return result


def load_offline_crypto_sample() -> pd.DataFrame:
    """Load bundled offline crypto sample data (if present)."""
    sample_path = "data/sample_crypto_data.csv"
    try:
        df = pd.read_csv(sample_path, parse_dates=["date"])
    except Exception:
        return pd.DataFrame()

    if df.empty:
        return df

    df = df.rename(columns={"symbol": "symbol", "close": "close", "volume": "volume"})
    return df
