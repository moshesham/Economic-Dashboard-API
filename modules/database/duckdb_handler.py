"""
DuckDB Database Connection Handler (updated to match base interface)
"""

import duckdb
import pandas as pd
from pathlib import Path
from typing import Optional
from .base import BaseDatabase


class DuckDBDatabase(BaseDatabase):
    """DuckDB database connection handler"""
    
    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or str(Path("data/duckdb/economic_dashboard.db"))
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self.conn = None
        self.connect()
        self._ensure_tables()
    
    def connect(self):
        """Establish DuckDB connection"""
        if self.conn is None:
            self.conn = duckdb.connect(self.db_path)
            # Configure DuckDB
            self.conn.execute("SET threads=4")
            self.conn.execute("SET memory_limit='2GB'")
    
    def execute(self, query: str, params: Optional[dict] = None):
        """Execute a query"""
        if params:
            # DuckDB uses $1, $2 style parameters
            self.conn.execute(query, list(params.values()))
        else:
            self.conn.execute(query)
    
    def query(self, query: str, params: Optional[dict] = None) -> pd.DataFrame:
        """Execute a query and return results as DataFrame"""
        if params:
            return self.conn.execute(query, list(params.values())).fetchdf()
        else:
            return self.conn.execute(query).fetchdf()
    
    def insert_dataframe(self, df: pd.DataFrame, table: str, if_exists: str = "append"):
        """Insert DataFrame into table"""
        if df.empty:
            return 0
        
        # DuckDB-specific efficient insert
        if if_exists == "replace":
            self.conn.execute(f"DELETE FROM {table}")
        
        # Use DuckDB's native DataFrame support
        self.conn.execute(f"INSERT INTO {table} SELECT * FROM df")
        return len(df)
    
    def get_row_count(self, table: str) -> int:
        """Get row count for a table"""
        result = self.conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()
        return result[0] if result else 0
    
    def _ensure_tables(self):
        """Create tables if they don't exist (DuckDB schema)"""
        # Import schema creation logic
        try:
            from .schema import create_tables
            create_tables(self.conn)
        except ImportError:
            pass  # Schema module not available yet
    
    def close(self):
        """Close DuckDB connection"""
        if self.conn:
            self.conn.close()
            self.conn = None
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
