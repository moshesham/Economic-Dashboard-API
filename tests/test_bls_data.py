"""Targeted tests for BLSDataLoader version routing and request payload behavior."""

from datetime import datetime

import pandas as pd

from modules.bls_data import BLSDataLoader


class _DummyResponse:
    def __init__(self, payload):
        self._payload = payload

    def json(self):
        return self._payload


class _DummyClient:
    def __init__(self):
        self.calls = []

    def post(self, endpoint, json=None, headers=None):
        self.calls.append({"endpoint": endpoint, "json": json, "headers": headers})
        return _DummyResponse(
            {
                "status": "REQUEST_SUCCEEDED",
                "Results": {
                    "series": [
                        {
                            "seriesID": "LNS14000000",
                            "data": [
                                {
                                    "year": "2024",
                                    "period": "M01",
                                    "value": "3.7",
                                    "footnotes": [{"text": "prelim"}],
                                }
                            ],
                        }
                    ]
                },
            }
        )

    def close(self):
        return None


def test_bls_loader_uses_v1_without_real_key(monkeypatch):
    monkeypatch.setenv("BLS_API_KEY", "your_bls_api_key_here")
    loader = BLSDataLoader()
    assert loader.version == "v1"
    assert loader.api_key is None
    assert loader.base_endpoint == "/timeseries/data/"


def test_bls_loader_uses_v2_with_key():
    loader = BLSDataLoader(api_key="real-key")
    assert loader.version == "v2"
    assert loader.api_key == "real-key"


def test_fetch_series_v1_payload_and_endpoint(monkeypatch):
    dummy = _DummyClient()
    loader = BLSDataLoader(api_key=None)
    loader.client = dummy

    df = loader.fetch_series(series_ids=["LNS14000000"], start_year=2024, end_year=2024)

    assert not df.empty
    assert isinstance(df, pd.DataFrame)
    assert dummy.calls
    call = dummy.calls[0]
    assert call["endpoint"] == "/timeseries/data/"
    assert call["json"]["seriesid"] == ["LNS14000000"]
    assert call["json"]["startyear"] == "2024"
    assert call["json"]["endyear"] == "2024"
    assert "registrationkey" not in call["json"]


def test_fetch_series_v2_payload_includes_registration_key():
    dummy = _DummyClient()
    loader = BLSDataLoader(api_key="real-key")
    loader.client = dummy

    loader.fetch_series(series_ids=["LNS14000000"], start_year=2024, end_year=2024)

    call = dummy.calls[0]
    assert call["json"]["registrationkey"] == "real-key"
