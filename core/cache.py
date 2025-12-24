"""
Redis-based caching module for API responses.

Provides decorators and middleware for caching API responses with configurable TTL.
"""

import hashlib
import json
import logging
from functools import wraps
from typing import Any, Callable, Optional
from datetime import timedelta

try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from core.config import settings

logger = logging.getLogger(__name__)


class CacheManager:
    """Manages Redis-based caching with connection pooling."""
    
    def __init__(self, redis_url: Optional[str] = None):
        """
        Initialize cache manager.
        
        Args:
            redis_url: Redis connection URL (uses settings.REDIS_URL if not provided)
        """
        self.redis_url = redis_url or settings.REDIS_URL
        self._client: Optional[Any] = None
        self._enabled = REDIS_AVAILABLE
        
    @property
    def client(self) -> Any:
        """Get or create Redis client with connection pooling."""
        if not REDIS_AVAILABLE:
            logger.warning("Redis not available. Caching disabled.")
            return DummyRedisClient()
            
        if self._client is None:
            try:
                self._client = redis.from_url(
                    self.redis_url,
                    decode_responses=True,
                    socket_connect_timeout=5,
                    socket_timeout=5,
                    max_connections=50,
                )
                # Test connection
                self._client.ping()
                logger.info("Redis cache connection established")
            except Exception as e:
                logger.warning(f"Failed to connect to Redis: {e}. Caching disabled.")
                self._enabled = False
                self._client = DummyRedisClient()
        return self._client
    
    def get(self, key: str) -> Optional[str]:
        """Get value from cache."""
        if not self._enabled:
            return None
        try:
            return self.client.get(key)
        except Exception as e:
            logger.warning(f"Cache get error: {e}")
            return None
    
    def set(self, key: str, value: str, ttl: int = None) -> bool:
        """
        Set value in cache.
        
        Args:
            key: Cache key
            value: Value to cache
            ttl: Time to live in seconds (uses REDIS_CACHE_TTL if not provided)
            
        Returns:
            True if successful, False otherwise
        """
        if not self._enabled:
            return False
        try:
            ttl = ttl or settings.REDIS_CACHE_TTL
            return bool(self.client.setex(key, ttl, value))
        except Exception as e:
            logger.warning(f"Cache set error: {e}")
            return False
    
    def delete(self, key: str) -> bool:
        """Delete key from cache."""
        if not self._enabled:
            return False
        try:
            return bool(self.client.delete(key))
        except Exception as e:
            logger.warning(f"Cache delete error: {e}")
            return False
    
    def delete_pattern(self, pattern: str) -> int:
        """
        Delete all keys matching pattern.
        
        Args:
            pattern: Redis key pattern (e.g., "api:data:*")
            
        Returns:
            Number of keys deleted
        """
        if not self._enabled:
            return 0
        try:
            keys = self.client.keys(pattern)
            if keys:
                return self.client.delete(*keys)
            return 0
        except Exception as e:
            logger.warning(f"Cache delete pattern error: {e}")
            return 0
    
    def get_stats(self) -> dict:
        """Get cache statistics."""
        if not self._enabled:
            return {"enabled": False}
        try:
            info = self.client.info("stats")
            return {
                "enabled": True,
                "total_commands": info.get("total_commands_processed", 0),
                "keyspace_hits": info.get("keyspace_hits", 0),
                "keyspace_misses": info.get("keyspace_misses", 0),
                "used_memory_human": self.client.info("memory").get("used_memory_human", "N/A"),
            }
        except Exception as e:
            logger.warning(f"Cache stats error: {e}")
            return {"enabled": False, "error": str(e)}


class DummyRedisClient:
    """Dummy Redis client that does nothing (for when Redis is unavailable)."""
    
    def get(self, key: str) -> None:
        return None
    
    def setex(self, key: str, ttl: int, value: str) -> bool:
        return False
    
    def delete(self, *keys) -> int:
        return 0
    
    def keys(self, pattern: str) -> list:
        return []
    
    def ping(self) -> bool:
        return True
    
    def info(self, section: str) -> dict:
        return {}


# Global cache manager instance
cache_manager = CacheManager()


def cache_key(*args, **kwargs) -> str:
    """
    Generate cache key from arguments.
    
    Args:
        *args: Positional arguments
        **kwargs: Keyword arguments
        
    Returns:
        MD5 hash of serialized arguments
    """
    key_data = {
        "args": args,
        "kwargs": {k: v for k, v in sorted(kwargs.items())}
    }
    key_str = json.dumps(key_data, sort_keys=True, default=str)
    return hashlib.md5(key_str.encode()).hexdigest()


def cached(
    ttl: Optional[int] = None,
    key_prefix: str = "api",
    key_builder: Optional[Callable] = None
):
    """
    Decorator to cache function results in Redis.
    
    Args:
        ttl: Time to live in seconds (default: settings.REDIS_CACHE_TTL)
        key_prefix: Prefix for cache keys
        key_builder: Custom function to build cache key
        
    Example:
        @cached(ttl=300, key_prefix="data:fred")
        async def get_fred_data(series_id: str):
            ...
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Build cache key
            if key_builder:
                cache_key_str = key_builder(*args, **kwargs)
            else:
                cache_key_str = cache_key(*args, **kwargs)
            
            full_key = f"{key_prefix}:{func.__name__}:{cache_key_str}"
            
            # Try to get from cache
            cached_value = cache_manager.get(full_key)
            if cached_value is not None:
                logger.debug(f"Cache hit: {full_key}")
                try:
                    return json.loads(cached_value)
                except json.JSONDecodeError:
                    logger.warning(f"Failed to decode cached value for {full_key}")
            
            # Cache miss - call function
            logger.debug(f"Cache miss: {full_key}")
            result = await func(*args, **kwargs)
            
            # Store in cache
            try:
                cache_manager.set(full_key, json.dumps(result, default=str), ttl)
            except Exception as e:
                logger.warning(f"Failed to cache result for {full_key}: {e}")
            
            return result
        return wrapper
    return decorator


class CacheMiddleware(BaseHTTPMiddleware):
    """
    Middleware to cache GET requests to API endpoints.
    
    Automatically caches responses for GET requests with status code 200.
    """
    
    def __init__(self, app, ttl: int = None, cache_paths: list = None):
        """
        Initialize cache middleware.
        
        Args:
            app: FastAPI application
            ttl: Default TTL for cached responses
            cache_paths: List of path prefixes to cache
        """
        super().__init__(app)
        self.ttl = ttl or settings.REDIS_CACHE_TTL
        self.cache_paths = cache_paths or ["/v1/data", "/v1/features", "/v1/predictions", "/v1/signals"]
    
    async def dispatch(self, request: Request, call_next):
        """Process request and cache if applicable."""
        # Only cache GET requests
        if request.method != "GET":
            return await call_next(request)
        
        # Check if path should be cached
        path = request.url.path
        should_cache = any(path.startswith(prefix) for prefix in self.cache_paths)
        
        if not should_cache:
            return await call_next(request)
        
        # Build cache key from path and query params
        query_params = dict(request.query_params)
        cache_key_str = f"{path}:{cache_key(**query_params)}"
        full_key = f"http_cache:{cache_key_str}"
        
        # Try to get from cache
        cached_response = cache_manager.get(full_key)
        if cached_response is not None:
            logger.debug(f"HTTP cache hit: {path}")
            try:
                cached_data = json.loads(cached_response)
                return Response(
                    content=json.dumps(cached_data["content"]),
                    status_code=cached_data["status_code"],
                    headers={
                        **cached_data.get("headers", {}),
                        "X-Cache": "HIT",
                    },
                    media_type="application/json"
                )
            except Exception as e:
                logger.warning(f"Failed to return cached response: {e}")
        
        # Cache miss - process request
        response = await call_next(request)
        
        # Cache successful responses
        if response.status_code == 200:
            # Read response body
            body = b""
            async for chunk in response.body_iterator:
                body += chunk
            
            try:
                # Parse and cache
                response_data = {
                    "content": json.loads(body.decode()),
                    "status_code": response.status_code,
                    "headers": dict(response.headers),
                }
                cache_manager.set(full_key, json.dumps(response_data, default=str), self.ttl)
                logger.debug(f"HTTP cache miss: {path}")
                
                # Return response with cached body
                return Response(
                    content=body,
                    status_code=response.status_code,
                    headers={**response.headers, "X-Cache": "MISS"},
                    media_type=response.media_type
                )
            except Exception as e:
                logger.warning(f"Failed to cache response: {e}")
                return Response(
                    content=body,
                    status_code=response.status_code,
                    headers=response.headers,
                    media_type=response.media_type
                )
        
        return response


# Utility functions
def invalidate_cache(pattern: str = "*") -> int:
    """Invalidate cache entries matching pattern."""
    return cache_manager.delete_pattern(pattern)


def get_cache_stats() -> dict:
    """Get cache statistics."""
    return cache_manager.get_stats()
