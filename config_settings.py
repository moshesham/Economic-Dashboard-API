"""
Configuration settings for the Economic Dashboard.
Controls offline mode and caching behavior.

DEPRECATED: This module is deprecated and maintained only for backward compatibility.
Please import from core.config instead:
    from core.config import is_offline_mode, can_use_offline_data, get_cache_dir, ensure_cache_dir
    from core.config import settings  # For CACHE_EXPIRY_HOURS, YFINANCE_* constants

This file will be removed in a future version.
"""

import warnings

# Issue deprecation warning when this module is imported
warnings.warn(
    "config_settings is deprecated. Use 'from core.config import ...' instead. "
    "This module will be removed in a future version.",
    DeprecationWarning,
    stacklevel=2
)

# Import everything from core.config for backward compatibility
from core.config import (
    is_offline_mode,
    can_use_offline_data,
    get_cache_dir,
    ensure_cache_dir,
    DATA_SOURCES,
    CACHE_EXPIRY_HOURS,
    YFINANCE_RATE_LIMIT_DELAY,
    YFINANCE_BATCH_SIZE,
    YFINANCE_CACHE_HOURS,
    settings
)

# Backward compatibility aliases
OFFLINE_MODE = settings.OFFLINE_MODE
CACHE_DIR = settings.CACHE_DIR

SAMPLE_DATA_AVAILABLE = {
    'fred': can_use_offline_data('fred'),
    'yfinance': can_use_offline_data('yfinance'),
    'world_bank': can_use_offline_data('world_bank')
}
