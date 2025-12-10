"""Unit tests for InsiderTradingTracker core analytics."""

from datetime import datetime, timedelta

import pandas as pd
import pytest

from modules.features.insider_trading_tracker import InsiderTradingTracker


@pytest.fixture
def tracker() -> InsiderTradingTracker:
    """Return a fresh tracker instance for each test."""
    return InsiderTradingTracker()


@pytest.fixture
def sample_transactions() -> pd.DataFrame:
    """Synthetic insider transaction data covering recent and baseline periods."""
    now = datetime.now()

    def make_transaction(days_ago: int, code: str, value: float, insider: str, title: str) -> dict:
        txn_date = now - timedelta(days=days_ago)
        price = 100.0
        shares = value / price
        is_buy = code in {"P", "M"}
        return {
            "transaction_date": txn_date,
            "filing_date": txn_date + timedelta(days=1),
            "insider_name": insider,
            "insider_title": title,
            "is_director": "director" in title.lower(),
            "is_officer": "chief" in title.lower() or "vp" in title.lower(),
            "transaction_code": code,
            "transaction_type": "Open Market Purchase" if code == "P" else (
                "Exercise of Options" if code == "M" else "Open Market Sale"
            ),
            "shares": shares,
            "price_per_share": price,
            "transaction_value": value,
            "acquired_disposed": "A" if is_buy else "D",
            "shares_owned_after": 10000,
            "security_type": "Common Stock",
        }

    recent = [
        make_transaction(10, "P", 150_000, "Alice CEO", "Chief Executive Officer"),
        make_transaction(20, "P", 60_000, "Bob CFO", "Chief Financial Officer"),
        make_transaction(15, "M", 40_000, "Cara VP", "Vice President"),
        make_transaction(5, "S", 50_000, "Evan Director", "Director"),
    ]

    baseline = [
        make_transaction(140, "P", 20_000, "Frank Director", "Director"),
    ]

    return pd.DataFrame(recent + baseline)


def test_calculate_insider_sentiment_identifies_bullish_bias(tracker: InsiderTradingTracker, sample_transactions: pd.DataFrame):
    """Sentiment should be bullish when recent insider buys outweigh sells."""
    sentiment = tracker.calculate_insider_sentiment(sample_transactions, days=90)

    assert sentiment["sentiment_score"] > 0
    assert sentiment["buy_value"] > sentiment["sell_value"]
    assert sentiment["num_buyers"] == 3
    assert sentiment["signal"] in {"Buy", "Strong Buy"}


def test_detect_unusual_activity_flags_volume_spike(tracker: InsiderTradingTracker, sample_transactions: pd.DataFrame):
    """Unusual activity detection should fire when recent volume dwarfs baseline."""
    activity = tracker.detect_unusual_activity(sample_transactions, lookback_days=60, baseline_days=240)

    assert activity["is_unusual"] is True
    assert activity["volume_ratio"] >= 2
    assert any("Transaction volume" in alert for alert in activity["alerts"])


def test_get_top_insider_buyers_returns_ranked_output(tracker: InsiderTradingTracker, sample_transactions: pd.DataFrame):
    """Top buyers list should be ordered by descending transaction value."""
    top_buyers = tracker.get_top_insider_buyers(sample_transactions, days=60, top_n=2)

    assert not top_buyers.empty
    assert len(top_buyers) == 2
    assert top_buyers.iloc[0]["Insider"] == "Alice CEO"
    assert top_buyers.iloc[0]["Total Value"] >= top_buyers.iloc[1]["Total Value"]
