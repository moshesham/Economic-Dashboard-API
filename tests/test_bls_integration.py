"""Tests for BLS series catalog and database query helper integration."""

import pandas as pd

from modules.bls_data import BLS_SERIES, BLS_SERIES_CATEGORIES
from modules.database.queries import get_bls_data


class _DummyDB:
    def __init__(self):
        self.last_query = None
        self.last_params = None

    def query(self, query, params=None):
        self.last_query = query
        self.last_params = params
        return pd.DataFrame([
            {
                "series_id": "LNS14000000",
                "series_name": "Unemployment Rate (U-3)",
                "year": 2024,
                "period": "M01",
                "date": "2024-01-01",
                "value": 3.7,
            }
        ])


def test_bls_series_flattened_from_categories():
    expected_total = sum(len(series_map) for series_map in BLS_SERIES_CATEGORIES.values())
    assert len(BLS_SERIES) == expected_total

    # Spot-check key additions from each category
    assert "LNS13327709" in BLS_SERIES  # U-6
    assert "JTS000000000000000JOL" in BLS_SERIES  # JOLTS openings
    assert "CUSR0000SA0L1E" in BLS_SERIES  # Core CPI-U
    assert "PRS85006093" in BLS_SERIES  # Productivity index


def test_get_bls_data_builds_parameterized_query(monkeypatch):
    dummy_db = _DummyDB()

    def _fake_get_db_connection():
        return dummy_db

    monkeypatch.setattr("modules.database.queries.get_db_connection", _fake_get_db_connection)

    df = get_bls_data(
        series_ids=["LNS14000000", "LNS13327709"],
        start_date="2023-01-01",
        end_date="2024-12-31",
        limit=50,
    )

    assert not df.empty
    assert "FROM bls_data" in dummy_db.last_query
    assert "series_id IN (?, ?)" in dummy_db.last_query
    assert "date >= ?" in dummy_db.last_query
    assert "date <= ?" in dummy_db.last_query
    assert "LIMIT ?" in dummy_db.last_query
    assert dummy_db.last_params == (
        "LNS14000000",
        "LNS13327709",
        "2023-01-01",
        "2024-12-31",
        50,
    )


def test_get_bls_data_without_filters(monkeypatch):
    dummy_db = _DummyDB()

    def _fake_get_db_connection():
        return dummy_db

    monkeypatch.setattr("modules.database.queries.get_db_connection", _fake_get_db_connection)

    _ = get_bls_data()

    assert "FROM bls_data" in dummy_db.last_query
    assert dummy_db.last_params is None
