"""
Base Database Connection Handler
Supports both DuckDB (dev) and PostgreSQL (prod)
"""

import os
from typing import Optional, Literal
from abc import ABC, abstractmethod
import pandas as pd


DatabaseBackend = Literal["duckdb", "postgresql"]


class BaseDatabase(ABC):
    """Abstract base class for database connections"""
    
    @abstractmethod
    def connect(self):
        """Establish database connection"""
        pass
    
    @abstractmethod
    def execute(self, query: str, params: Optional[dict] = None):
        """Execute a query"""
        pass
    
    @abstractmethod
    def query(self, query: str, params: Optional[dict] = None) -> pd.DataFrame:
        """Execute a query and return results as DataFrame"""
        pass
    
    @abstractmethod
    def insert_dataframe(self, df: pd.DataFrame, table: str, if_exists: str = "append"):
        """Insert DataFrame into table"""
        pass
    
    @abstractmethod
    def get_row_count(self, table: str) -> int:
        """Get row count for a table"""
        pass
    
    @abstractmethod
    def close(self):
        """Close database connection"""
        pass


def get_database_backend() -> DatabaseBackend:
    """Determine which database backend to use based on environment"""
    backend = os.getenv("DATABASE_BACKEND", "duckdb").lower()
    if backend not in ["duckdb", "postgresql"]:
        raise ValueError(f"Invalid DATABASE_BACKEND: {backend}. Must be 'duckdb' or 'postgresql'")
    return backend
