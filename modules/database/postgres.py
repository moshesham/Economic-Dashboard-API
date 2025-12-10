"""
PostgreSQL Database Connection Handler
"""

import os
import psycopg2
from psycopg2.extras import execute_values, RealDictCursor
import pandas as pd
from typing import Optional
from .base import BaseDatabase


class PostgreSQLDatabase(BaseDatabase):
    """PostgreSQL database connection handler"""
    
    def __init__(self):
        self.conn = None
        self.connect()
    
    def connect(self):
        """Establish PostgreSQL connection"""
        if self.conn is not None and not self.conn.closed:
            return
        
        database_url = os.getenv("DATABASE_URL")
        
        if database_url:
            # Parse DATABASE_URL (for cloud deployments)
            self.conn = psycopg2.connect(database_url)
        else:
            # Use individual environment variables
            self.conn = psycopg2.connect(
                host=os.getenv("POSTGRES_HOST", "localhost"),
                port=int(os.getenv("POSTGRES_PORT", 5432)),
                database=os.getenv("POSTGRES_DB", "economic_dashboard"),
                user=os.getenv("POSTGRES_USER", "dashboard_user"),
                password=os.getenv("POSTGRES_PASSWORD", "dashboard_pass")
            )
        
        self.conn.autocommit = False
    
    def execute(self, query: str, params: Optional[dict] = None):
        """Execute a query with optional parameters"""
        with self.conn.cursor() as cur:
            cur.execute(query, params)
            self.conn.commit()
    
    def query(self, query: str, params: Optional[dict] = None) -> pd.DataFrame:
        """Execute a query and return results as DataFrame"""
        return pd.read_sql_query(query, self.conn, params=params)
    
    def insert_dataframe(self, df: pd.DataFrame, table: str, if_exists: str = "append"):
        """Insert DataFrame into PostgreSQL table using efficient batch insert"""
        if df.empty:
            return 0
        
        # Prepare column names and values
        columns = df.columns.tolist()
        values = [tuple(row) for row in df.itertuples(index=False, name=None)]
        
        # Build INSERT query
        cols_str = ", ".join(columns)
        
        if if_exists == "replace":
            # Truncate table first
            with self.conn.cursor() as cur:
                cur.execute(f"TRUNCATE TABLE {table}")
        
        # Use execute_values for efficient batch insert with ON CONFLICT handling
        insert_query = f"""
            INSERT INTO {table} ({cols_str}) 
            VALUES %s
            ON CONFLICT DO NOTHING
        """
        
        with self.conn.cursor() as cur:
            execute_values(cur, insert_query, values)
            self.conn.commit()
            return len(values)
    
    def get_row_count(self, table: str) -> int:
        """Get row count for a table"""
        with self.conn.cursor() as cur:
            cur.execute(f"SELECT COUNT(*) FROM {table}")
            result = cur.fetchone()
            return result[0] if result else 0
    
    def close(self):
        """Close PostgreSQL connection"""
        if self.conn and not self.conn.closed:
            self.conn.close()
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            self.conn.rollback()
        self.close()
