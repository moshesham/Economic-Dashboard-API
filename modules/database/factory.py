"""
Database Factory - Multi-Backend Support

Provides abstraction layer for DuckDB (dev) and PostgreSQL (prod).
"""

import os
import logging
from typing import Optional, Protocol, Any
from pathlib import Path
import pandas as pd
from contextlib import contextmanager

logger = logging.getLogger(__name__)


class DatabaseBackend(Protocol):
    """Protocol defining the interface all database backends must implement."""
    
    def query(self, sql: str, params: Optional[tuple] = None) -> pd.DataFrame:
        """Execute a SELECT query and return results as DataFrame."""
        ...
    
    def execute(self, sql: str, params: Optional[tuple] = None) -> None:
        """Execute a non-SELECT query."""
        ...
    
    def insert_df(self, df: pd.DataFrame, table_name: str, if_exists: str = 'append') -> None:
        """Insert a pandas DataFrame into a table."""
        ...
    
    def table_exists(self, table_name: str) -> bool:
        """Check if a table exists."""
        ...
    
    def get_row_count(self, table_name: str) -> int:
        """Get the number of rows in a table."""
        ...
    
    def close(self) -> None:
        """Close the database connection."""
        ...


class DuckDBBackend:
    """DuckDB implementation of DatabaseBackend."""
    
    def __init__(self, db_path: Optional[Path] = None, read_only: bool = False):
        import duckdb
        from datetime import datetime
        
        self.db_path = db_path or Path(__file__).parent.parent.parent / 'data' / 'duckdb' / 'economic_dashboard.duckdb'
        self.read_only = read_only
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Create temp directory
        self.temp_dir = self.db_path.parent / 'temp'
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        
        db_existed = self.db_path.exists()
        
        try:
            self._connection = duckdb.connect(str(self.db_path), read_only=read_only)
            self._configure_connection()
            
            if not db_existed and not read_only:
                logger.info("DuckDB database not found. Initializing new schema at %s", self.db_path)
                self._initialize_schema()
                
        except duckdb.Error as exc:
            if self._should_recover_database(exc, self.db_path):
                self._recover_corrupt_database(self.db_path)
                self._connection = duckdb.connect(str(self.db_path), read_only=read_only)
                self._configure_connection()
                if not read_only:
                    self._initialize_schema()
            else:
                raise
    
    def _configure_connection(self) -> None:
        """Apply DuckDB-specific configuration."""
        self._connection.execute("SET threads=4")
        self._connection.execute("SET memory_limit='2GB'")
        self._connection.execute(f"SET temp_directory='{self.temp_dir}'")
    
    @staticmethod
    def _should_recover_database(exc: Exception, db_path: Path) -> bool:
        """Determine if the database should be automatically recovered."""
        import duckdb
        corruption_markers = ("Corrupt database file", "checksum", "IO Error")
        return (
            isinstance(exc, duckdb.IOException)
            and db_path.exists()
            and any(marker in str(exc) for marker in corruption_markers)
        )
    
    def _recover_corrupt_database(self, db_path: Path) -> None:
        """Backup the corrupt database file and create a clean one."""
        from datetime import datetime
        timestamp = datetime.utcnow().strftime('%Y%m%d%H%M%S')
        backup_name = f"{db_path.stem}.corrupt-{timestamp}{db_path.suffix}"
        backup_path = db_path.with_name(backup_name)
        
        try:
            db_path.rename(backup_path)
            logger.error(
                "Corrupt DuckDB detected at %s. Backed up to %s before re-initializing.",
                db_path, backup_path
            )
        except OSError as rename_error:
            logger.exception("Failed to backup corrupt DuckDB at %s.", db_path)
            raise rename_error
    
    def _initialize_schema(self) -> None:
        """Create all necessary tables for a new database."""
        from .schema import create_all_tables
        create_all_tables()
    
    def query(self, sql: str, params: Optional[tuple] = None) -> pd.DataFrame:
        """Execute a SELECT query and return results as DataFrame."""
        if params:
            return self._connection.execute(sql, params).df()
        return self._connection.execute(sql).df()
    
    def execute(self, sql: str, params: Optional[tuple] = None) -> None:
        """Execute a non-SELECT query."""
        if params:
            self._connection.execute(sql, params)
        else:
            self._connection.execute(sql)
        self._connection.commit()
    
    def insert_df(self, df: pd.DataFrame, table_name: str, if_exists: str = 'append') -> None:
        """Insert a pandas DataFrame into a table."""
        self._connection.register('temp_df', df)
        
        if if_exists == 'replace':
            self.execute(f"DELETE FROM {table_name}")
        
        columns = ', '.join(df.columns)
        self.execute(f"INSERT INTO {table_name} ({columns}) SELECT {columns} FROM temp_df")
        self._connection.unregister('temp_df')
    
    def table_exists(self, table_name: str) -> bool:
        """Check if a table exists."""
        result = self.query(
            "SELECT COUNT(*) as count FROM information_schema.tables WHERE table_name = ?",
            (table_name,)
        )
        return result['count'].iloc[0] > 0
    
    def get_row_count(self, table_name: str) -> int:
        """Get the number of rows in a table."""
        result = self.query(f"SELECT COUNT(*) as count FROM {table_name}")
        return int(result['count'].iloc[0])
    
    def close(self) -> None:
        """Close the database connection."""
        if hasattr(self, '_connection') and self._connection:
            self._connection.close()
            self._connection = None


class PostgreSQLBackend:
    """PostgreSQL implementation of DatabaseBackend."""
    
    def __init__(self, connection_url: Optional[str] = None):
        import psycopg2
        import psycopg2.extras
        from psycopg2 import pool
        
        self.connection_url = connection_url or self._build_connection_url()
        
        # Create connection pool for better performance
        self._pool = pool.ThreadedConnectionPool(
            minconn=1,
            maxconn=10,
            dsn=self.connection_url
        )
        
        logger.info("PostgreSQL connection pool established")
        
        # Initialize schema if needed
        self._initialize_schema()
    
    @staticmethod
    def _build_connection_url() -> str:
        """Build connection URL from environment variables."""
        # Try DATABASE_URL first
        url = os.getenv('DATABASE_URL')
        if url:
            return url
        
        # Build from individual components
        host = os.getenv('POSTGRES_HOST', 'localhost')
        port = os.getenv('POSTGRES_PORT', '5432')
        database = os.getenv('POSTGRES_DB', 'economic_dashboard')
        user = os.getenv('POSTGRES_USER', 'dashboard_user')
        password = os.getenv('POSTGRES_PASSWORD', 'dashboard_pass')
        
        return f"postgresql://{user}:{password}@{host}:{port}/{database}"
    
    def _get_connection(self):
        """Get a connection from the pool."""
        return self._pool.getconn()
    
    def _return_connection(self, conn):
        """Return a connection to the pool."""
        self._pool.putconn(conn)
    
    def _initialize_schema(self) -> None:
        """Create all necessary tables if they don't exist."""
        from .postgres_schema import create_all_tables
        create_all_tables(self)
    
    def query(self, sql: str, params: Optional[tuple] = None) -> pd.DataFrame:
        """Execute a SELECT query and return results as DataFrame."""
        import psycopg2.extras
        
        conn = self._get_connection()
        try:
            # Use RealDictCursor for dictionary-like results
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                cursor.execute(sql, params)
                results = cursor.fetchall()
                
                if not results:
                    return pd.DataFrame()
                
                return pd.DataFrame(results)
        finally:
            self._return_connection(conn)
    
    def execute(self, sql: str, params: Optional[tuple] = None) -> None:
        """Execute a non-SELECT query."""
        conn = self._get_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute(sql, params)
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            self._return_connection(conn)
    
    def insert_df(self, df: pd.DataFrame, table_name: str, if_exists: str = 'append') -> None:
        """Insert a pandas DataFrame into a table using bulk insert."""
        if df.empty:
            return
        
        if if_exists == 'replace':
            self.execute(f"TRUNCATE TABLE {table_name}")
        
        # Use pandas to_sql for efficient bulk insert
        from sqlalchemy import create_engine
        engine = create_engine(self.connection_url)
        
        df.to_sql(
            table_name,
            engine,
            if_exists='append',
            index=False,
            method='multi',
            chunksize=1000
        )
        
        engine.dispose()
    
    def table_exists(self, table_name: str) -> bool:
        """Check if a table exists."""
        result = self.query(
            """
            SELECT COUNT(*) as count 
            FROM information_schema.tables 
            WHERE table_schema = 'public' AND table_name = %s
            """,
            (table_name,)
        )
        return result['count'].iloc[0] > 0
    
    def get_row_count(self, table_name: str) -> int:
        """Get the number of rows in a table."""
        result = self.query(f"SELECT COUNT(*) as count FROM {table_name}")
        return int(result['count'].iloc[0])
    
    def close(self) -> None:
        """Close all connections in the pool."""
        if hasattr(self, '_pool') and self._pool:
            self._pool.closeall()
            logger.info("PostgreSQL connection pool closed")


class DatabaseConnection:
    """Singleton database connection manager with multi-backend support."""
    
    _instance: Optional['DatabaseConnection'] = None
    _backend: Optional[DatabaseBackend] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if self._backend is None:
            self._initialize_backend()
    
    def _initialize_backend(self) -> None:
        """Initialize the appropriate database backend based on configuration."""
        backend_type = os.getenv('DATABASE_BACKEND', 'duckdb').lower()
        
        if backend_type == 'postgresql':
            logger.info("Initializing PostgreSQL backend")
            self._backend = PostgreSQLBackend()
        elif backend_type == 'duckdb':
            logger.info("Initializing DuckDB backend")
            read_only = os.getenv('DUCKDB_READ_ONLY', 'false').lower() == 'true'
            db_path_str = os.getenv('DUCKDB_PATH')
            db_path = Path(db_path_str) if db_path_str else None
            self._backend = DuckDBBackend(db_path=db_path, read_only=read_only)
        else:
            raise ValueError(f"Unsupported database backend: {backend_type}")
    
    # Delegate all methods to the backend
    def query(self, sql: str, params: Optional[tuple] = None) -> pd.DataFrame:
        """Execute a SELECT query and return results as DataFrame."""
        return self._backend.query(sql, params)
    
    def execute(self, sql: str, params: Optional[tuple] = None) -> None:
        """Execute a non-SELECT query."""
        return self._backend.execute(sql, params)
    
    def insert_df(self, df: pd.DataFrame, table_name: str, if_exists: str = 'append') -> None:
        """Insert a pandas DataFrame into a table."""
        return self._backend.insert_df(df, table_name, if_exists)
    
    def table_exists(self, table_name: str) -> bool:
        """Check if a table exists."""
        return self._backend.table_exists(table_name)
    
    def get_row_count(self, table_name: str) -> int:
        """Get the number of rows in a table."""
        return self._backend.get_row_count(table_name)
    
    def close(self) -> None:
        """Close the database connection."""
        if self._backend:
            self._backend.close()
            self._backend = None


# Global instance for singleton access
_db_connection = None

def get_db_connection() -> DatabaseConnection:
    """Get the singleton database connection instance."""
    global _db_connection
    if _db_connection is None:
        _db_connection = DatabaseConnection()
    return _db_connection

def get_backend() -> DatabaseBackend:
    """Get the current database backend."""
    return get_db_connection()._backend

def close_db_connection() -> None:
    """Close the database connection."""
    global _db_connection
    if _db_connection:
        _db_connection.close()
        _db_connection = None


# Module-level singleton
_db = DatabaseConnection()


def get_db_connection() -> DatabaseConnection:
    """Get the singleton database connection."""
    return _db


def close_db_connection():
    """Close the database connection."""
    _db.close()


def init_database():
    """Initialize the database schema."""
    # Schema initialization is now handled in backend constructors
    pass


@contextmanager
def db_transaction():
    """Context manager for database transactions."""
    conn = get_db_connection()
    try:
        yield conn
        # Commit is handled by execute()
    except Exception as e:
        # Rollback is handled by PostgreSQL backend
        raise e
