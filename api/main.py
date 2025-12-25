"""
Economic Dashboard API - Main Application Entry Point

FastAPI-based REST API for economic data, predictions, and analytics.
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
import logging
import os

from api.v1.routes import data, features, predictions, signals, portfolio, health, ingest
from core.config import settings
from core.logging import setup_logging
from core.middleware import RequestLoggingMiddleware
from core.cache import CacheMiddleware

# Setup logging
setup_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifecycle manager."""
    # Startup
    logger.info("Starting Economic Dashboard API...")
    logger.info(f"Environment: {settings.ENVIRONMENT}")
    logger.info(f"DuckDB Path: {settings.DUCKDB_PATH}")
    
    # Initialize database connection
    from modules.database import get_db_connection
    try:
        db = get_db_connection()
        logger.info("Database connection established")
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
    
    # Log cache status
    from core.cache import get_cache_stats
    cache_stats = get_cache_stats()
    logger.info(f"Cache status: {cache_stats}")
    
    yield
    
    # Shutdown
    logger.info("Shutting down Economic Dashboard API...")
    from modules.database import close_db_connection
    close_db_connection()


# Create FastAPI application
app = FastAPI(
    title="Economic Dashboard API",
    description="""
## Economic Data & Analytics API

A comprehensive API for accessing:
- **Economic Data**: FRED, SEC, Yahoo Finance data
- **Feature Engineering**: Technical indicators, options metrics, derived features
- **ML Predictions**: Multi-horizon stock predictions with explainability
- **Trading Signals**: Margin risk, insider activity, recession probability
- **Portfolio Optimization**: Black-Litterman allocation recommendations

### Authentication
Use API key in header: `X-API-Key: your-api-key`

### Rate Limiting
- Standard: 100 requests/minute
- Premium: 1000 requests/minute

### Caching
GET requests are cached with Redis. Cache status is indicated in response headers via `X-Cache: HIT|MISS`.
    """,
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

# Middleware (order matters - first added is executed last)
# 1. CORS (most outer)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# 2. GZip compression
app.add_middleware(GZipMiddleware, minimum_size=1000)
# 3. Request logging with correlation IDs
app.add_middleware(RequestLoggingMiddleware)
# 4. Response caching (most inner - executes first)
app.add_middleware(CacheMiddleware)

# Include routers
app.include_router(health.router, tags=["Health"])
app.include_router(data.router, prefix="/v1/data", tags=["Data"])
app.include_router(features.router, prefix="/v1/features", tags=["Features"])
app.include_router(predictions.router, prefix="/v1/predictions", tags=["Predictions"])
app.include_router(signals.router, prefix="/v1/signals", tags=["Signals"])
app.include_router(portfolio.router, prefix="/v1/portfolio", tags=["Portfolio"])
app.include_router(ingest.router, prefix="/v1", tags=["Ingestion"])


@app.get("/")
async def root():
    """API root - welcome message and links."""
    return {
        "name": "Economic Dashboard API",
        "version": "2.0.0",
        "docs": "/docs",
        "health": "/health",
        "endpoints": {
            "data": "/v1/data",
            "features": "/v1/features",
            "predictions": "/v1/predictions",
            "signals": "/v1/signals",
            "portfolio": "/v1/portfolio",
        }
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
