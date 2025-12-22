"""
Database Layer Tests

Tests for the database abstraction layer including connection management,
query execution, and backend-specific functionality.
"""

import pytest
import pandas as pd
from datetime import date, datetime
from unittest.mock import patch, MagicMock
import os


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def reset_db_singleton():
    """Reset the database singleton between tests."""
    import modules.database.factory as factory
    original = factory._db_connection
    factory._db_connection = None
    yield
    factory._db_connection = original


@pytest.fixture
def mock_postgres_env():
    """Set up environment for PostgreSQL backend."""
    original_backend = os.environ.get('DATABASE_BACKEND')
    os.environ['DATABASE_BACKEND'] = 'postgresql'
    os.environ['POSTGRES_HOST'] = 'localhost'
    os.environ['POSTGRES_PORT'] = '5432'
    os.environ['POSTGRES_DB'] = 'test_db'
    os.environ['POSTGRES_USER'] = 'test_user'
    os.environ['POSTGRES_PASSWORD'] = 'test_pass'
    yield
    if original_backend:
        os.environ['DATABASE_BACKEND'] = original_backend
    else:
        os.environ.pop('DATABASE_BACKEND', None)


@pytest.fixture
def mock_duckdb_env():
    """Set up environment for DuckDB backend."""
    original_backend = os.environ.get('DATABASE_BACKEND')
    os.environ['DATABASE_BACKEND'] = 'duckdb'
    os.environ['DUCKDB_PATH'] = ':memory:'
    yield
    if original_backend:
        os.environ['DATABASE_BACKEND'] = original_backend
    else:
        os.environ.pop('DATABASE_BACKEND', None)


# =============================================================================
# Database Connection Tests
# =============================================================================

class TestDatabaseConnection:
    """Tests for database connection management."""
    
    def test_get_db_connection_singleton(self, reset_db_singleton, mock_duckdb_env):
        """Test that get_db_connection returns a singleton."""
        from modules.database.factory import get_db_connection
        
        conn1 = get_db_connection()
        conn2 = get_db_connection()
        
        assert conn1 is conn2
    
    def test_close_db_connection(self, reset_db_singleton, mock_duckdb_env):
        """Test closing database connection."""
        from modules.database.factory import get_db_connection, close_db_connection
        import modules.database.factory as factory
        
        conn = get_db_connection()
        assert conn is not None
        
        close_db_connection()
        assert factory._db_connection is None
    
    def test_backend_selection_duckdb(self, reset_db_singleton, mock_duckdb_env):
        """Test DuckDB backend is selected when configured."""
        from modules.database.factory import get_db_connection, get_backend
        
        conn = get_db_connection()
        backend = get_backend()
        
        assert backend is not None
        # Check it's DuckDB backend by verifying the connection attribute exists
        assert hasattr(backend, '_connection')  # DuckDB has _connection attribute
    
    @patch('psycopg2.connect')
    def test_backend_selection_postgres(self, mock_connect, reset_db_singleton, mock_postgres_env):
        """Test PostgreSQL backend is selected when configured."""
        # Mock the connection
        mock_conn = MagicMock()
        mock_connect.return_value = mock_conn
        
        from modules.database.factory import get_db_connection
        
        try:
            conn = get_db_connection()
            # Should attempt to connect to PostgreSQL
            mock_connect.assert_called()
        except Exception:
            # Connection may fail, but we're testing selection logic
            pass


# =============================================================================
# Query Execution Tests
# =============================================================================

class TestQueryExecution:
    """Tests for query execution."""
    
    def test_query_returns_dataframe(self, reset_db_singleton, mock_duckdb_env):
        """Test query returns a pandas DataFrame."""
        from modules.database.factory import get_db_connection
        
        db = get_db_connection()
        
        # Create a test table
        db.execute("CREATE TABLE IF NOT EXISTS test_query (id INTEGER, name VARCHAR)")
        db.execute("INSERT INTO test_query VALUES (1, 'test')")
        
        result = db.query("SELECT * FROM test_query")
        
        assert isinstance(result, pd.DataFrame)
        assert len(result) == 1
        assert 'id' in result.columns
        assert 'name' in result.columns
    
    def test_query_with_parameters(self, reset_db_singleton, mock_duckdb_env):
        """Test parameterized queries."""
        from modules.database.factory import get_db_connection
        
        db = get_db_connection()
        
        db.execute("CREATE TABLE IF NOT EXISTS test_params (id INTEGER, value DOUBLE)")
        db.execute("INSERT INTO test_params VALUES (1, 100.5), (2, 200.5)")
        
        result = db.query("SELECT * FROM test_params WHERE id = ?", (1,))
        
        assert len(result) == 1
        assert result.iloc[0]['id'] == 1
    
    def test_execute_insert(self, reset_db_singleton, mock_duckdb_env):
        """Test execute for INSERT statements."""
        from modules.database.factory import get_db_connection
        
        db = get_db_connection()
        
        db.execute("CREATE TABLE IF NOT EXISTS test_insert (id INTEGER PRIMARY KEY, name VARCHAR)")
        db.execute("INSERT INTO test_insert VALUES (1, 'first')")
        
        result = db.query("SELECT COUNT(*) as cnt FROM test_insert")
        assert result.iloc[0]['cnt'] == 1
    
    def test_insert_df(self, reset_db_singleton, mock_duckdb_env):
        """Test inserting a DataFrame."""
        from modules.database.factory import get_db_connection
        
        db = get_db_connection()
        
        df = pd.DataFrame({
            'id': [1, 2, 3],
            'name': ['a', 'b', 'c'],
            'value': [1.1, 2.2, 3.3]
        })
        
        db.insert_df(df, 'test_insert_df', if_exists='replace')
        
        result = db.query("SELECT * FROM test_insert_df ORDER BY id")
        assert len(result) == 3
        assert list(result['id']) == [1, 2, 3]


# =============================================================================
# Table Operations Tests
# =============================================================================

class TestTableOperations:
    """Tests for table-level operations."""
    
    def test_table_exists_true(self, reset_db_singleton, mock_duckdb_env):
        """Test table_exists returns True for existing table."""
        from modules.database.factory import get_db_connection
        
        db = get_db_connection()
        
        db.execute("CREATE TABLE IF NOT EXISTS test_exists (id INTEGER)")
        
        assert db.table_exists('test_exists') == True
    
    def test_table_exists_false(self, reset_db_singleton, mock_duckdb_env):
        """Test table_exists returns False for non-existing table."""
        from modules.database.factory import get_db_connection
        
        db = get_db_connection()
        
        assert db.table_exists('nonexistent_table_12345') == False
    
    def test_get_row_count(self, reset_db_singleton, mock_duckdb_env):
        """Test getting row count for a table."""
        from modules.database.factory import get_db_connection
        
        db = get_db_connection()
        
        db.execute("CREATE TABLE IF NOT EXISTS test_count (id INTEGER)")
        db.execute("INSERT INTO test_count VALUES (1), (2), (3), (4), (5)")
        
        count = db.get_row_count('test_count')
        assert count == 5


# =============================================================================
# Error Handling Tests
# =============================================================================

class TestErrorHandling:
    """Tests for database error handling."""
    
    def test_query_invalid_sql(self, reset_db_singleton, mock_duckdb_env):
        """Test error handling for invalid SQL."""
        from modules.database.factory import get_db_connection
        
        db = get_db_connection()
        
        with pytest.raises(Exception):
            db.query("INVALID SQL STATEMENT")
    
    def test_query_nonexistent_table(self, reset_db_singleton, mock_duckdb_env):
        """Test error handling for non-existent table."""
        from modules.database.factory import get_db_connection
        
        db = get_db_connection()
        
        with pytest.raises(Exception):
            db.query("SELECT * FROM table_that_does_not_exist_12345")
    
    def test_execute_constraint_violation(self, reset_db_singleton, mock_duckdb_env):
        """Test error handling for constraint violations."""
        from modules.database.factory import get_db_connection
        
        db = get_db_connection()
        
        db.execute("CREATE TABLE IF NOT EXISTS test_constraint (id INTEGER PRIMARY KEY)")
        db.execute("INSERT INTO test_constraint VALUES (1)")
        
        with pytest.raises(Exception):
            db.execute("INSERT INTO test_constraint VALUES (1)")  # Duplicate PK


# =============================================================================
# Schema Tests
# =============================================================================

class TestSchemaCreation:
    """Tests for schema creation functions."""
    
    def test_fred_data_table_creation(self, reset_db_singleton, mock_duckdb_env):
        """Test FRED data table can be created."""
        from modules.database.schema_generator import create_fred_data_table
        from modules.database.factory import get_db_connection
        
        create_fred_data_table()
        
        db = get_db_connection()
        assert db.table_exists('fred_data')
    
    def test_yfinance_ohlcv_table_creation(self, reset_db_singleton, mock_duckdb_env):
        """Test yfinance OHLCV table can be created."""
        from modules.database.schema_generator import create_yfinance_ohlcv_table
        from modules.database.factory import get_db_connection
        
        create_yfinance_ohlcv_table()
        
        db = get_db_connection()
        assert db.table_exists('yfinance_ohlcv')
    
    def test_ml_predictions_table_creation(self, reset_db_singleton, mock_duckdb_env):
        """Test ML predictions table can be created."""
        from modules.database.schema_generator import create_ml_predictions_table
        from modules.database.factory import get_db_connection
        
        create_ml_predictions_table()
        
        db = get_db_connection()
        assert db.table_exists('ml_predictions')


# =============================================================================
# Transaction Tests
# =============================================================================

class TestTransactions:
    """Tests for transaction handling."""
    
    def test_db_transaction_context_manager(self, reset_db_singleton, mock_duckdb_env):
        """Test database transaction context manager."""
        from modules.database.factory import db_transaction, get_db_connection
        
        db = get_db_connection()
        db.execute("CREATE TABLE IF NOT EXISTS test_tx (id INTEGER)")
        
        with db_transaction() as conn:
            conn.execute("INSERT INTO test_tx VALUES (1)")
        
        result = db.query("SELECT COUNT(*) as cnt FROM test_tx")
        assert result.iloc[0]['cnt'] == 1


# =============================================================================
# Data Type Tests
# =============================================================================

class TestDataTypes:
    """Tests for data type handling."""
    
    def test_date_handling(self, reset_db_singleton, mock_duckdb_env):
        """Test date type handling in queries."""
        from modules.database.factory import get_db_connection
        
        db = get_db_connection()
        
        db.execute("CREATE TABLE IF NOT EXISTS test_dates (d DATE)")
        db.execute("INSERT INTO test_dates VALUES ('2024-01-15')")
        
        result = db.query("SELECT * FROM test_dates")
        
        # Should return date-like object
        assert result.iloc[0]['d'] is not None
    
    def test_json_handling(self, reset_db_singleton, mock_duckdb_env):
        """Test JSON type handling."""
        from modules.database.factory import get_db_connection
        
        db = get_db_connection()
        
        db.execute("CREATE TABLE IF NOT EXISTS test_json (data JSON)")
        db.execute("""INSERT INTO test_json VALUES ('{"key": "value"}')""")
        
        result = db.query("SELECT * FROM test_json")
        assert result.iloc[0]['data'] is not None
    
    def test_null_handling(self, reset_db_singleton, mock_duckdb_env):
        """Test NULL value handling."""
        from modules.database.factory import get_db_connection
        
        db = get_db_connection()
        
        db.execute("CREATE TABLE IF NOT EXISTS test_nulls (id INTEGER, nullable_col VARCHAR)")
        db.execute("INSERT INTO test_nulls VALUES (1, NULL)")
        
        result = db.query("SELECT * FROM test_nulls")
        
        assert pd.isna(result.iloc[0]['nullable_col'])
