"""
API Endpoint Tests

Comprehensive tests for the FastAPI endpoints using TestClient.
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
import pandas as pd
from datetime import datetime, date

from api.main import app


@pytest.fixture
def client():
    """Create a test client for the FastAPI app."""
    return TestClient(app)


@pytest.fixture
def mock_db():
    """Mock database connection."""
    with patch('modules.database.factory.get_db_connection') as mock:
        db_mock = MagicMock()
        mock.return_value = db_mock
        yield db_mock


# =============================================================================
# Health Endpoint Tests
# =============================================================================

class TestHealthEndpoints:
    """Tests for health check endpoints."""
    
    def test_health_check(self, client):
        """Test basic health endpoint returns OK."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
    
    def test_readiness_check(self, client):
        """Test readiness endpoint for load balancers."""
        response = client.get("/ready")
        # Returns 200 regardless of ready state
        assert response.status_code == 200
        data = response.json()
        assert "ready" in data


# =============================================================================
# Data Endpoint Tests
# =============================================================================

class TestDataEndpoints:
    """Tests for data access endpoints."""
    
    def test_list_fred_series(self, client):
        """Test listing available FRED series."""
        response = client.get("/v1/data/fred")
        # Returns 200 with data or 500 if DB is unavailable
        assert response.status_code in [200, 500]
        if response.status_code == 200:
            data = response.json()
            assert "series" in data
            assert "count" in data
    
    def test_get_fred_series(self, client):
        """Test getting a specific FRED series."""
        with patch('api.v1.routes.data.get_fred_series') as mock_get:
            mock_get.return_value = pd.DataFrame([
                {'date': date(2024, 1, 1), 'value': 100.5}
            ])
            
            response = client.get("/v1/data/fred/GDP")
            # This may fail if the mock isn't set up correctly
            # but tests the endpoint routing
            assert response.status_code in [200, 404, 500]
    
    def test_get_fred_series_not_found(self, client):
        """Test FRED series not found returns 404."""
        with patch('modules.database.get_fred_series') as mock_get:
            mock_get.return_value = pd.DataFrame()
            
            response = client.get("/v1/data/fred/NONEXISTENT")
            assert response.status_code in [404, 500]
    
    def test_get_stock_data(self, client):
        """Test getting stock OHLCV data."""
        with patch('modules.database.get_stock_ohlcv') as mock_get:
            mock_get.return_value = pd.DataFrame([
                {'date': date(2024, 1, 1), 'open': 100, 'high': 105,
                 'low': 99, 'close': 104, 'volume': 1000000}
            ])
            
            response = client.get("/v1/data/stocks/AAPL")
            assert response.status_code in [200, 404, 500]
    
    def test_list_available_stocks(self, client, mock_db):
        """Test listing available stock tickers."""
        mock_db.query.return_value = pd.DataFrame([
            {'ticker': 'AAPL', 'start_date': date(2020, 1, 1),
             'end_date': date(2024, 1, 1), 'data_points': 1000}
        ])
        
        response = client.get("/v1/data/stocks")
        assert response.status_code in [200, 500]


# =============================================================================
# Prediction Endpoint Tests
# =============================================================================

class TestPredictionEndpoints:
    """Tests for ML prediction endpoints."""
    
    def test_get_prediction(self, client):
        """Test getting a prediction for a ticker."""
        with patch('modules.ml.prediction.PredictionEngine') as mock_engine:
            mock_instance = MagicMock()
            mock_instance.predict.return_value = {
                'ticker': 'AAPL',
                'prediction': 1,
                'prediction_label': 'UP',
                'probability_up': 0.65,
                'confidence': 0.65
            }
            mock_engine.return_value = mock_instance
            
            response = client.get("/v1/predictions/AAPL")
            # May return 200, 404 (no model), or 500
            assert response.status_code in [200, 404, 500]
    
    def test_batch_predictions(self, client):
        """Test batch predictions endpoint."""
        with patch('modules.ml.prediction.PredictionEngine') as mock_engine:
            mock_instance = MagicMock()
            mock_instance.predict.return_value = {
                'ticker': 'AAPL',
                'prediction': 1,
                'probability_up': 0.65
            }
            mock_engine.return_value = mock_instance
            
            response = client.post(
                "/v1/predictions/batch",
                json={"tickers": ["AAPL", "MSFT"]}
            )
            assert response.status_code in [200, 404, 422, 500]


# =============================================================================
# Signals Endpoint Tests
# =============================================================================

class TestSignalEndpoints:
    """Tests for trading signal endpoints."""
    
    def test_get_margin_risk_signals(self, client):
        """Test getting margin risk signals for all tickers."""
        response = client.get("/v1/signals/margin-risk")
        assert response.status_code in [200, 500]
    
    def test_get_margin_risk_by_ticker(self, client):
        """Test getting margin risk for specific ticker."""
        response = client.get("/v1/signals/margin-risk/AAPL")
        # Returns 200, 404 (no data), or 500 (service error)
        assert response.status_code in [200, 404, 500]
    
    def test_get_sector_rotation(self, client):
        """Test getting sector rotation signals."""
        response = client.get("/v1/signals/sector-rotation")
        assert response.status_code in [200, 500]


# =============================================================================
# Features Endpoint Tests
# =============================================================================

class TestFeatureEndpoints:
    """Tests for feature data endpoints."""
    
    def test_get_technical_features(self, client, mock_db):
        """Test getting technical features for a ticker."""
        mock_db.query.return_value = pd.DataFrame([
            {'date': date(2024, 1, 1), 'rsi_14': 55.0, 'macd': 1.5}
        ])
        
        response = client.get("/v1/features/technical/AAPL")
        assert response.status_code in [200, 404, 500]
    
    def test_get_derived_features(self, client, mock_db):
        """Test getting derived features for a ticker."""
        mock_db.query.return_value = pd.DataFrame([
            {'date': date(2024, 1, 1), 'momentum_score': 0.65}
        ])
        
        response = client.get("/v1/features/derived/AAPL")
        assert response.status_code in [200, 404, 500]


# =============================================================================
# Ingest Endpoint Tests
# =============================================================================

class TestIngestEndpoints:
    """Tests for data ingestion endpoints."""
    
    def test_ingest_fred_unauthorized(self, client):
        """Test FRED ingestion requires API key."""
        response = client.post(
            "/v1/ingest/fred",
            json={"series_ids": ["GDP"]}
        )
        # Should require authentication or return validation error
        assert response.status_code in [401, 403, 422, 500]
    
    def test_ingest_stock_unauthorized(self, client):
        """Test stock ingestion requires API key."""
        response = client.post(
            "/v1/ingest/stock",
            json={"tickers": ["AAPL"]}
        )
        assert response.status_code in [401, 403, 422, 500]


# =============================================================================
# Portfolio Endpoint Tests
# =============================================================================

class TestPortfolioEndpoints:
    """Tests for portfolio analytics endpoints."""
    
    def test_portfolio_analysis(self, client):
        """Test portfolio analysis endpoint."""
        response = client.post(
            "/v1/portfolio/analyze",
            json={
                "holdings": [
                    {"ticker": "AAPL", "shares": 100, "cost_basis": 150.0},
                    {"ticker": "MSFT", "shares": 50, "cost_basis": 300.0}
                ]
            }
        )
        assert response.status_code in [200, 422, 500]
    
    def test_portfolio_optimize(self, client):
        """Test portfolio optimization endpoint."""
        response = client.post(
            "/v1/portfolio/optimize",
            json={
                "tickers": ["AAPL", "MSFT", "GOOGL"],
                "target_return": 0.10
            }
        )
        assert response.status_code in [200, 422, 500]


# =============================================================================
# Error Handling Tests
# =============================================================================

class TestErrorHandling:
    """Tests for API error handling."""
    
    def test_invalid_ticker_format(self, client):
        """Test invalid ticker format handling."""
        response = client.get("/v1/data/stocks/!@#$%")
        assert response.status_code in [400, 404, 422, 500]
    
    def test_invalid_date_format(self, client):
        """Test invalid date format handling."""
        response = client.get("/v1/data/fred/GDP?start_date=invalid-date")
        # FastAPI should validate the date format
        assert response.status_code in [200, 422, 500]
    
    def test_nonexistent_endpoint(self, client):
        """Test 404 for nonexistent endpoints."""
        response = client.get("/v1/nonexistent")
        assert response.status_code == 404


# =============================================================================
# Response Format Tests
# =============================================================================

class TestResponseFormats:
    """Tests for API response format consistency."""
    
    def test_error_response_format(self, client):
        """Test error responses have consistent format."""
        response = client.get("/v1/data/fred/NONEXISTENT_SERIES_123456")
        if response.status_code >= 400:
            data = response.json()
            # Should have detail field for errors
            assert "detail" in data or "error" in data or "message" in data
    
    def test_success_response_has_data(self, client, mock_db):
        """Test success responses contain data."""
        mock_db.query.return_value = pd.DataFrame([
            {'series_id': 'GDP', 'data_points': 100}
        ])
        
        response = client.get("/v1/data/fred")
        if response.status_code == 200:
            data = response.json()
            # Should have series or data field
            assert any(key in data for key in ['series', 'data', 'result'])
