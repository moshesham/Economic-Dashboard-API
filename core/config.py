"""
Core configuration module.

Manages all application settings via environment variables.
"""

import os
from pathlib import Path
from typing import List, Optional
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Environment
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    
    # API Configuration
    API_KEY_ENABLED: bool = True
    API_SECRET_KEY: str = "change-me-in-production"
    API_RATE_LIMIT: int = 100  # requests per minute
    CORS_ORIGINS: List[str] = ["*"]
    
    # Database
    DUCKDB_PATH: str = str(Path(__file__).parent.parent / "data" / "duckdb" / "economic_dashboard.duckdb")
    DUCKDB_READ_ONLY: bool = False
    DUCKDB_MEMORY_LIMIT: str = "4GB"
    DUCKDB_THREADS: int = 4
    
    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_CACHE_TTL: int = 3600  # 1 hour default cache TTL
    
    # External API Keys
    FRED_API_KEY: Optional[str] = None
    ALPHA_VANTAGE_API_KEY: Optional[str] = None
    NEWS_API_KEY: Optional[str] = None
    OPENAI_API_KEY: Optional[str] = None
    
    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    # Worker Configuration
    WORKER_REFRESH_CRON: str = "0 6 * * *"
    WORKER_CLEANUP_CRON: str = "0 2 * * 0"
    WORKER_COMPACT_CRON: str = "0 3 * * 0"
    
    # Feature Flags
    ENABLE_LLM_SENTIMENT: bool = False
    ENABLE_REAL_TIME_SIGNALS: bool = False
    ENABLE_PORTFOLIO_OPTIMIZATION: bool = False
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


# Global settings instance
settings = get_settings()
