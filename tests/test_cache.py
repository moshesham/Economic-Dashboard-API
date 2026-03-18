"""
Tests for cache module.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from core.cache import (
    CacheManager,
    DummyRedisClient,
    cache_key,
    cached,
    invalidate_cache,
    get_cache_stats,
)


class TestCacheManager:
    """Tests for CacheManager class."""
    
    def test_cache_manager_initialization(self):
        """Test cache manager can be initialized."""
        manager = CacheManager()
        assert manager is not None
        assert manager.redis_url is not None
    
    def test_dummy_redis_client(self):
        """Test dummy Redis client when Redis is unavailable."""
        client = DummyRedisClient()
        assert client.get("test") is None
        assert client.setex("test", 60, "value") is False
        assert client.delete("test") == 0
        assert client.keys("*") == []
        assert client.ping() is True
        assert client.info("stats") == {}
    
    @patch('core.cache.REDIS_AVAILABLE', False)
    def test_cache_manager_without_redis(self):
        """Test cache manager when Redis is not available."""
        manager = CacheManager()
        assert manager.get("test") is None
        assert manager.set("test", "value") is False
        assert manager.delete("test") is False
    
    def test_cache_key_generation(self):
        """Test cache key generation from arguments."""
        key1 = cache_key("arg1", "arg2", kwarg1="value1")
        key2 = cache_key("arg1", "arg2", kwarg1="value1")
        key3 = cache_key("arg1", "arg2", kwarg1="value2")
        
        # Same arguments should generate same key
        assert key1 == key2
        # Different arguments should generate different key
        assert key1 != key3
    
    @patch('core.cache.REDIS_AVAILABLE', True)
    @patch('core.cache.redis')
    def test_cache_set_get(self, mock_redis):
        """Test setting and getting values from cache."""
        # Setup mock
        mock_client = MagicMock()
        mock_client.ping.return_value = True
        mock_client.get.return_value = "test_value"
        mock_client.setex.return_value = True
        mock_redis.from_url.return_value = mock_client
        
        # Test
        manager = CacheManager()
        assert manager.set("test_key", "test_value", 60) is True
        assert manager.get("test_key") == "test_value"
    
    @patch('core.cache.REDIS_AVAILABLE', True)
    @patch('core.cache.redis')
    def test_cache_delete(self, mock_redis):
        """Test deleting values from cache."""
        # Setup mock
        mock_client = MagicMock()
        mock_client.ping.return_value = True
        mock_client.delete.return_value = 1
        mock_redis.from_url.return_value = mock_client
        
        # Test
        manager = CacheManager()
        assert manager.delete("test_key") is True
    
    @patch('core.cache.REDIS_AVAILABLE', True)
    @patch('core.cache.redis')
    def test_cache_stats(self, mock_redis):
        """Test getting cache statistics."""
        # Setup mock
        mock_client = MagicMock()
        mock_client.ping.return_value = True
        mock_client.info.return_value = {
            "total_commands_processed": 100,
            "keyspace_hits": 75,
            "keyspace_misses": 25,
            "used_memory_human": "1.5M",
        }
        mock_redis.from_url.return_value = mock_client
        
        # Test
        manager = CacheManager()
        stats = manager.get_stats()
        assert stats["enabled"] is True
        assert stats["total_commands"] == 100
        assert stats["keyspace_hits"] == 75


class TestCachedDecorator:
    """Tests for cached decorator."""
    
    @pytest.mark.asyncio
    @patch('core.cache.cache_manager')
    async def test_cached_decorator_cache_hit(self, mock_manager):
        """Test cached decorator returns cached value on cache hit."""
        mock_manager.get.return_value = '{"result": "cached"}'
        
        @cached(ttl=60)
        async def test_function():
            return {"result": "fresh"}
        
        result = await test_function()
        assert result == {"result": "cached"}
    
    @pytest.mark.asyncio
    @patch('core.cache.cache_manager')
    async def test_cached_decorator_cache_miss(self, mock_manager):
        """Test cached decorator calls function on cache miss."""
        mock_manager.get.return_value = None
        mock_manager.set.return_value = True
        
        @cached(ttl=60)
        async def test_function():
            return {"result": "fresh"}
        
        result = await test_function()
        assert result == {"result": "fresh"}
        assert mock_manager.set.called


class TestCacheUtilities:
    """Tests for cache utility functions."""
    
    @patch('core.cache.cache_manager')
    def test_invalidate_cache(self, mock_manager):
        """Test cache invalidation."""
        mock_manager.delete_pattern.return_value = 5
        
        count = invalidate_cache("test:*")
        assert count == 5
        mock_manager.delete_pattern.assert_called_once_with("test:*")
    
    @patch('core.cache.cache_manager')
    def test_get_cache_stats(self, mock_manager):
        """Test getting cache statistics."""
        mock_manager.get_stats.return_value = {"enabled": True, "hits": 100}
        
        stats = get_cache_stats()
        assert stats["enabled"] is True
        assert stats["hits"] == 100
