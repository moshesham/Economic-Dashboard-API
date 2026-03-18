"""
Tests for middleware (request logging and caching).
"""

import pytest
from fastapi import FastAPI, Request, Response
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from core.middleware import RequestLoggingMiddleware
from core.cache import CacheMiddleware
from core.logging import get_correlation_id, set_correlation_id


class TestRequestLoggingMiddleware:
    """Tests for RequestLoggingMiddleware."""
    
    def test_middleware_adds_correlation_id(self):
        """Test middleware adds correlation ID to response."""
        app = FastAPI()
        app.add_middleware(RequestLoggingMiddleware)
        
        @app.get("/test")
        async def test_endpoint():
            return {"message": "test"}
        
        client = TestClient(app)
        response = client.get("/test")
        
        assert response.status_code == 200
        assert "X-Correlation-ID" in response.headers
    
    def test_middleware_uses_provided_correlation_id(self):
        """Test middleware uses correlation ID from request header."""
        app = FastAPI()
        app.add_middleware(RequestLoggingMiddleware)
        
        @app.get("/test")
        async def test_endpoint():
            return {"message": "test"}
        
        client = TestClient(app)
        test_correlation_id = "test-123-456"
        response = client.get("/test", headers={"X-Correlation-ID": test_correlation_id})
        
        assert response.status_code == 200
        assert response.headers["X-Correlation-ID"] == test_correlation_id
    
    def test_middleware_logs_request_details(self):
        """Test middleware logs request details."""
        app = FastAPI()
        app.add_middleware(RequestLoggingMiddleware)
        
        @app.get("/test")
        async def test_endpoint():
            return {"message": "test"}
        
        with patch('core.middleware.logger') as mock_logger:
            client = TestClient(app)
            response = client.get("/test?param=value")
            
            assert response.status_code == 200
            # Verify logging was called
            assert mock_logger.info.call_count >= 2  # Started and completed


class TestCacheMiddleware:
    """Tests for CacheMiddleware."""
    
    @patch('core.cache.cache_manager')
    def test_cache_middleware_cache_hit(self, mock_cache_manager):
        """Test cache middleware returns cached response."""
        app = FastAPI()
        app.add_middleware(CacheMiddleware)
        
        call_count = 0
        
        @app.get("/v1/data/test")
        async def test_endpoint():
            nonlocal call_count
            call_count += 1
            return {"data": "fresh"}
        
        # Mock cache hit
        import json
        cached_response = json.dumps({
            "content": {"data": "cached"},
            "status_code": 200,
            "headers": {}
        })
        mock_cache_manager.get.return_value = cached_response
        
        client = TestClient(app)
        response = client.get("/v1/data/test")
        
        assert response.status_code == 200
        assert response.headers.get("X-Cache") == "HIT"
        assert call_count == 0  # Endpoint not called
    
    @patch('core.cache.cache_manager')
    def test_cache_middleware_cache_miss(self, mock_cache_manager):
        """Test cache middleware caches response on miss."""
        app = FastAPI()
        app.add_middleware(CacheMiddleware)
        
        @app.get("/v1/data/test")
        async def test_endpoint():
            return {"data": "fresh"}
        
        # Mock cache miss
        mock_cache_manager.get.return_value = None
        mock_cache_manager.set.return_value = True
        
        client = TestClient(app)
        response = client.get("/v1/data/test")
        
        assert response.status_code == 200
        assert response.headers.get("X-Cache") == "MISS"
        assert mock_cache_manager.set.called
    
    def test_cache_middleware_only_caches_get(self):
        """Test cache middleware only caches GET requests."""
        app = FastAPI()
        app.add_middleware(CacheMiddleware)
        
        @app.post("/v1/data/test")
        async def test_endpoint():
            return {"data": "fresh"}
        
        with patch('core.cache.cache_manager') as mock_cache_manager:
            client = TestClient(app)
            response = client.post("/v1/data/test")
            
            assert response.status_code == 200
            # Cache should not be checked for POST
            assert not mock_cache_manager.get.called
    
    @patch('core.cache.cache_manager')
    def test_cache_middleware_respects_cache_paths(self, mock_cache_manager):
        """Test cache middleware only caches configured paths."""
        app = FastAPI()
        app.add_middleware(CacheMiddleware, cache_paths=["/v1/data"])
        
        @app.get("/v1/data/test")
        async def cached_endpoint():
            return {"data": "cached"}
        
        @app.get("/other/test")
        async def uncached_endpoint():
            return {"data": "uncached"}
        
        mock_cache_manager.get.return_value = None
        mock_cache_manager.set.return_value = True
        
        client = TestClient(app)
        
        # Cached path
        response1 = client.get("/v1/data/test")
        assert response1.status_code == 200
        
        # Reset mock
        mock_cache_manager.get.reset_mock()
        mock_cache_manager.set.reset_mock()
        
        # Uncached path
        response2 = client.get("/other/test")
        assert response2.status_code == 200
        # Cache should not be used for uncached path
        assert not mock_cache_manager.get.called
