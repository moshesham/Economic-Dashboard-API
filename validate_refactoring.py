"""
End-to-End Validation Script for Database Refactoring
Tests both DuckDB and PostgreSQL backends
"""

import os
import sys
import pandas as pd
from datetime import datetime

# Test configuration
TEST_RESULTS = []

def log_test(test_name, passed, message=""):
    """Log test result"""
    status = "✓ PASS" if passed else "✗ FAIL"
    TEST_RESULTS.append({
        'test': test_name,
        'passed': passed,
        'message': message
    })
    print(f"{status} - {test_name}")
    if message:
        print(f"    {message}")


def test_imports():
    """Test 1: Verify all imports work"""
    try:
        from modules.database.base import BaseDatabase, get_database_backend
        from modules.database.duckdb_handler import DuckDBDatabase
        from modules.database.postgres import PostgreSQLDatabase
        from modules.database.factory import get_db_connection, close_db_connection
        from modules.database import get_db_connection as main_import
        log_test("Module Imports", True, "All modules imported successfully")
        return True
    except Exception as e:
        log_test("Module Imports", False, str(e))
        return False


def test_backend_selection():
    """Test 2: Verify backend selection logic"""
    try:
        from modules.database.base import get_database_backend
        
        # Test default (DuckDB)
        os.environ.pop('DATABASE_BACKEND', None)
        backend = get_database_backend()
        assert backend == "duckdb", f"Expected 'duckdb', got '{backend}'"
        
        # Test PostgreSQL setting
        os.environ['DATABASE_BACKEND'] = 'postgresql'
        backend = get_database_backend()
        assert backend == "postgresql", f"Expected 'postgresql', got '{backend}'"
        
        # Reset to default
        os.environ['DATABASE_BACKEND'] = 'duckdb'
        
        log_test("Backend Selection", True, "Both backends selectable")
        return True
    except Exception as e:
        log_test("Backend Selection", False, str(e))
        return False


def test_duckdb_connection():
    """Test 3: DuckDB connection and basic operations"""
    try:
        from modules.database.duckdb_handler import DuckDBDatabase
        
        db = DuckDBDatabase()
        assert db.conn is not None, "Connection is None"
        
        # Test execute
        db.execute("CREATE TABLE IF NOT EXISTS test_conn (id INTEGER)")
        
        # Test insert
        df = pd.DataFrame({'id': [1, 2, 3]})
        records = db.insert_dataframe(df, 'test_conn', if_exists='replace')
        assert records == 3, f"Expected 3 records, inserted {records}"
        
        # Test query
        result = db.query("SELECT COUNT(*) as cnt FROM test_conn")
        assert result['cnt'].iloc[0] == 3, "Query returned wrong count"
        
        # Test get_row_count
        count = db.get_row_count('test_conn')
        assert count == 3, f"Expected 3, got {count}"
        
        # Cleanup
        db.execute("DROP TABLE test_conn")
        db.close()
        
        log_test("DuckDB Operations", True, "All CRUD operations work")
        return True
    except Exception as e:
        log_test("DuckDB Operations", False, str(e))
        return False


def test_factory_pattern():
    """Test 4: Factory pattern with DuckDB backend"""
    try:
        from modules.database.factory import get_db_connection, close_db_connection
        from modules.database.duckdb_handler import DuckDBDatabase
        
        # Ensure DuckDB backend
        os.environ['DATABASE_BACKEND'] = 'duckdb'
        
        db = get_db_connection()
        assert isinstance(db, DuckDBDatabase), f"Expected DuckDBDatabase, got {type(db)}"
        
        # Test singleton pattern
        db2 = get_db_connection()
        assert db is db2, "Factory should return same instance"
        
        # Test force_new
        db3 = get_db_connection(force_new=True)
        assert db3 is not db, "force_new should create new instance"
        
        close_db_connection()
        
        log_test("Factory Pattern", True, "Singleton and force_new work correctly")
        return True
    except Exception as e:
        log_test("Factory Pattern", False, str(e))
        return False


def test_main_module_exports():
    """Test 5: Main module exports work correctly"""
    try:
        from modules.database import get_db_connection
        
        db = get_db_connection()
        
        # Create test table
        db.execute("CREATE TABLE IF NOT EXISTS test_export (id INTEGER, value DOUBLE)")
        df = pd.DataFrame({'id': [1, 2], 'value': [10.5, 20.3]})
        db.insert_dataframe(df, 'test_export', if_exists='replace')
        
        # Query
        result = db.query("SELECT * FROM test_export ORDER BY id")
        assert len(result) == 2, "Wrong number of rows"
        assert result['value'].iloc[0] == 10.5, "Wrong value"
        
        # Cleanup
        db.execute("DROP TABLE test_export")
        
        log_test("Main Module Exports", True, "Exports work correctly")
        return True
    except Exception as e:
        log_test("Main Module Exports", False, str(e))
        return False


def test_batch_operations():
    """Test 6: Batch insert operations"""
    try:
        from modules.database import get_db_connection
        
        db = get_db_connection()
        
        # Create test table
        db.execute("CREATE TABLE IF NOT EXISTS test_batch (id INTEGER, name VARCHAR, value DOUBLE)")
        
        # Insert large batch
        large_df = pd.DataFrame({
            'id': range(1000),
            'name': [f'item_{i}' for i in range(1000)],
            'value': [i * 1.5 for i in range(1000)]
        })
        
        records = db.insert_dataframe(large_df, 'test_batch', if_exists='replace')
        assert records == 1000, f"Expected 1000 records, got {records}"
        
        count = db.get_row_count('test_batch')
        assert count == 1000, f"Expected 1000 in DB, got {count}"
        
        # Test append
        append_df = pd.DataFrame({
            'id': [1001, 1002],
            'name': ['item_1001', 'item_1002'],
            'value': [1001.5, 1002.5]
        })
        db.insert_dataframe(append_df, 'test_batch', if_exists='append')
        
        count = db.get_row_count('test_batch')
        assert count == 1002, f"Expected 1002 after append, got {count}"
        
        # Cleanup
        db.execute("DROP TABLE test_batch")
        
        log_test("Batch Operations", True, "Large batch inserts work correctly")
        return True
    except Exception as e:
        log_test("Batch Operations", False, str(e))
        return False


def test_context_manager():
    """Test 7: Context manager support"""
    try:
        from modules.database.duckdb_handler import DuckDBDatabase
        
        with DuckDBDatabase() as db:
            db.execute("CREATE TABLE IF NOT EXISTS test_context (id INTEGER)")
            df = pd.DataFrame({'id': [1]})
            db.insert_dataframe(df, 'test_context')
            count = db.get_row_count('test_context')
            assert count == 1, "Data not inserted"
            db.execute("DROP TABLE test_context")
        
        # Connection should be closed
        log_test("Context Manager", True, "Context manager works correctly")
        return True
    except Exception as e:
        log_test("Context Manager", False, str(e))
        return False


def test_postgres_import():
    """Test 8: PostgreSQL module can be imported (even if not connected)"""
    try:
        from modules.database.postgres import PostgreSQLDatabase
        
        # Just verify it can be imported
        assert PostgreSQLDatabase is not None
        
        log_test("PostgreSQL Import", True, "PostgreSQL module available")
        return True
    except Exception as e:
        log_test("PostgreSQL Import", False, str(e))
        return False


def test_backward_compatibility():
    """Test 9: Backward compatibility with old imports"""
    try:
        # These should still work even though we changed the implementation
        from modules.database import get_db_connection
        from modules.database import insert_fred_data, insert_stock_data
        from modules.database import get_fred_series, get_stock_ohlcv
        
        # All imports should succeed
        log_test("Backward Compatibility", True, "Old imports still work")
        return True
    except Exception as e:
        log_test("Backward Compatibility", False, str(e))
        return False


def test_empty_dataframe_handling():
    """Test 10: Handle empty DataFrames gracefully"""
    try:
        from modules.database import get_db_connection
        
        db = get_db_connection()
        db.execute("CREATE TABLE IF NOT EXISTS test_empty (id INTEGER, value DOUBLE)")
        
        # Try to insert empty DataFrame
        empty_df = pd.DataFrame(columns=['id', 'value'])
        records = db.insert_dataframe(empty_df, 'test_empty')
        
        assert records == 0, f"Expected 0 records, got {records}"
        
        count = db.get_row_count('test_empty')
        assert count == 0, f"Table should be empty, has {count} records"
        
        db.execute("DROP TABLE test_empty")
        
        log_test("Empty DataFrame Handling", True, "Empty DataFrames handled correctly")
        return True
    except Exception as e:
        log_test("Empty DataFrame Handling", False, str(e))
        return False


def print_summary():
    """Print test summary"""
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    total = len(TEST_RESULTS)
    passed = sum(1 for t in TEST_RESULTS if t['passed'])
    failed = total - passed
    
    print(f"\nTotal Tests: {total}")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    print(f"Success Rate: {(passed/total*100):.1f}%")
    
    if failed > 0:
        print("\nFailed Tests:")
        for test in TEST_RESULTS:
            if not test['passed']:
                print(f"  - {test['test']}: {test['message']}")
    
    print("\n" + "="*60)
    
    return failed == 0


def main():
    print("="*60)
    print("DATABASE REFACTORING - END-TO-END VALIDATION")
    print("="*60)
    print(f"Started: {datetime.now()}")
    print()
    
    # Ensure we're using DuckDB for tests
    os.environ['DATABASE_BACKEND'] = 'duckdb'
    
    # Run all tests
    tests = [
        test_imports,
        test_backend_selection,
        test_duckdb_connection,
        test_factory_pattern,
        test_main_module_exports,
        test_batch_operations,
        test_context_manager,
        test_postgres_import,
        test_backward_compatibility,
        test_empty_dataframe_handling,
    ]
    
    for test_func in tests:
        try:
            test_func()
        except Exception as e:
            print(f"✗ CRITICAL ERROR in {test_func.__name__}: {e}")
            TEST_RESULTS.append({
                'test': test_func.__name__,
                'passed': False,
                'message': f"Critical error: {e}"
            })
    
    # Print summary
    all_passed = print_summary()
    
    if all_passed:
        print("\n✅ ALL TESTS PASSED - System is working correctly!")
        sys.exit(0)
    else:
        print("\n❌ SOME TESTS FAILED - Review errors above")
        sys.exit(1)


if __name__ == "__main__":
    main()
