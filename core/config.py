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
    
    # Offline Mode & Caching (migrated from config_settings.py)
    OFFLINE_MODE: bool = False  # Set via ECONOMIC_DASHBOARD_OFFLINE env var
    CACHE_DIR: str = "data/cache"
    CACHE_EXPIRY_HOURS: int = 24
    
    # Yahoo Finance rate limiting
    YFINANCE_RATE_LIMIT_DELAY: float = 0.5
    YFINANCE_BATCH_SIZE: int = 5
    YFINANCE_CACHE_HOURS: int = 24
    
    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": True
    }
    
    def model_post_init(self, __context) -> None:
        """Override OFFLINE_MODE from ECONOMIC_DASHBOARD_OFFLINE env var if present."""
        offline_val = os.getenv('ECONOMIC_DASHBOARD_OFFLINE', '').lower()
        if offline_val in ('true', 'false'):
            object.__setattr__(self, 'OFFLINE_MODE', offline_val == 'true')


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


# Global settings instance
settings = get_settings()


# ============================================================================
# Offline Mode & Cache Helper Functions (migrated from config_settings.py)
# ============================================================================

def is_offline_mode() -> bool:
    """Check if offline mode is enabled."""
    return settings.OFFLINE_MODE


def get_cache_dir() -> str:
    """Get the cache directory path."""
    return settings.CACHE_DIR


def ensure_cache_dir() -> None:
    """Ensure cache directory exists."""
    os.makedirs(settings.CACHE_DIR, exist_ok=True)
    os.makedirs(f'{settings.CACHE_DIR}/yfinance/', exist_ok=True)


def can_use_offline_data(source: str) -> bool:
    """Check if offline data is available for a source."""
    sample_data_available = {
        'fred': os.path.exists('data/sample_fred_data.csv'),
        'yfinance': any(f.startswith('sample_') and f.endswith('_data.csv')
                       for f in os.listdir('data/') if os.path.isfile(os.path.join('data', f))),
        'world_bank': os.path.exists('data/sample_world_bank_gdp.csv')
    }
    return sample_data_available.get(source, False)


# Data sources configuration
DATA_SOURCES = {
    'fred': {
        'online': True,
        'offline_file': 'data/sample_fred_data.csv',
        'cache_file': f'{settings.CACHE_DIR}/fred_cache.pkl'
    },
    'yfinance': {
        'online': True,
        'offline_dir': 'data/',
        'cache_dir': f'{settings.CACHE_DIR}/yfinance/'
    },
    'world_bank': {
        'online': True,
        'offline_file': 'data/sample_world_bank_gdp.csv',
        'cache_file': f'{settings.CACHE_DIR}/world_bank_cache.pkl'
    }
}


# Backward compatibility exports
CACHE_EXPIRY_HOURS = settings.CACHE_EXPIRY_HOURS
YFINANCE_RATE_LIMIT_DELAY = settings.YFINANCE_RATE_LIMIT_DELAY
YFINANCE_BATCH_SIZE = settings.YFINANCE_BATCH_SIZE
YFINANCE_CACHE_HOURS = settings.YFINANCE_CACHE_HOURS

