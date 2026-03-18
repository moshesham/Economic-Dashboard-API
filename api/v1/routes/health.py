"""
Health check endpoints.
"""

from fastapi import APIRouter
from datetime import datetime
import os

router = APIRouter()


@router.get("/health")
async def health_check():
    """
    Health check endpoint for container orchestration.
    
    Returns:
        Health status with component checks
    """
    # Check database connection
    db_status = "healthy"
    try:
        from modules.database import get_db_connection
        db = get_db_connection()
        db.query("SELECT 1")
    except Exception as e:
        db_status = f"unhealthy: {str(e)}"
    
    # Check Redis connection
    redis_status = "healthy"
    try:
        import redis
        from core.config import settings
        r = redis.from_url(settings.REDIS_URL)
        r.ping()
    except Exception as e:
        redis_status = f"unhealthy: {str(e)}"
    
    # Check cache status
    cache_status = "healthy"
    try:
        from core.cache import get_cache_stats
        stats = get_cache_stats()
        if not stats.get("enabled"):
            cache_status = "disabled"
    except Exception as e:
        cache_status = f"error: {str(e)}"
    
    return {
        "status": "healthy" if db_status == "healthy" else "degraded",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "2.0.0",
        "components": {
            "database": db_status,
            "redis": redis_status,
            "cache": cache_status,
        },
        "environment": os.getenv("ENVIRONMENT", "development"),
    }


@router.get("/ready")
async def readiness_check():
    """
    Readiness check for load balancer.
    
    Returns:
        Ready status indicating if service can accept traffic
    """
    try:
        from modules.database import get_db_connection
        db = get_db_connection()
        
        # Check if essential tables exist
        tables = db.query("""
            SELECT table_name FROM information_schema.tables 
            WHERE table_schema = 'main'
        """)
        
        essential_tables = ['fred_data', 'yfinance_ohlcv']
        existing_tables = set(tables['table_name'].tolist()) if not tables.empty else set()
        
        missing = [t for t in essential_tables if t not in existing_tables]
        
        if missing:
            return {
                "ready": False,
                "reason": f"Missing tables: {missing}",
                "timestamp": datetime.utcnow().isoformat(),
            }
        
        return {
            "ready": True,
            "timestamp": datetime.utcnow().isoformat(),
        }
        
    except Exception as e:
        return {
            "ready": False,
            "reason": str(e),
            "timestamp": datetime.utcnow().isoformat(),
        }


@router.get("/cache/stats")
async def cache_stats():
    """
    Get cache statistics.
    
    Returns:
        Cache hit/miss statistics and memory usage
    """
    from core.cache import get_cache_stats
    return get_cache_stats()
