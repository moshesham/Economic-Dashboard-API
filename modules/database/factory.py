"""
Database Connection Factory
Returns appropriate database handler based on configuration
"""

import os
from typing import Union
from .base import BaseDatabase, get_database_backend
from .duckdb_handler import DuckDBDatabase
from .postgres import PostgreSQLDatabase


_db_instance: Union[BaseDatabase, None] = None


def get_db_connection(force_new: bool = False) -> BaseDatabase:
    """
    Get database connection based on DATABASE_BACKEND environment variable
    
    Args:
        force_new: If True, create a new connection instead of reusing singleton
    
    Returns:
        Database handler instance (DuckDB or PostgreSQL)
    """
    global _db_instance
    
    if force_new or _db_instance is None:
        backend = get_database_backend()
        
        if backend == "postgresql":
            _db_instance = PostgreSQLDatabase()
        else:  # duckdb
            _db_instance = DuckDBDatabase()
    
    return _db_instance


def close_db_connection():
    """Close the global database connection"""
    global _db_instance
    if _db_instance:
        _db_instance.close()
        _db_instance = None
