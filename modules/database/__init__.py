"""
DuckDB Database Module

Provides connection management, schema creation, and query interface for the Economic Dashboard.
"""

from .connection import get_db_connection, close_db_connection, init_database
from .queries import (
    get_fred_series,
    get_stock_ohlcv,
    get_options_data,
    get_technical_features,
    get_latest_predictions,
    get_model_performance,
    get_feature_importance,
    insert_fred_data,
    insert_stock_data,
    insert_options_data,
    insert_predictions,
    insert_technical_features,
)

__all__ = [
    'get_db_connection',
    'close_db_connection',
    'init_database',
    'get_fred_series',
    'get_stock_ohlcv',
    'get_options_data',
    'get_technical_features',
    'get_latest_predictions',
    'get_model_performance',
    'get_feature_importance',
    'insert_fred_data',
    'insert_stock_data',
    'insert_options_data',
    'insert_predictions',
    'insert_technical_features',
]
