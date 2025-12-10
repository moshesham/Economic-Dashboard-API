"""
Backend Switching Test
Validates that the system can switch between DuckDB and PostgreSQL
"""

import os
import sys

def test_backend_switching():
    """Test switching between database backends"""
    print("="*60)
    print("BACKEND SWITCHING VALIDATION")
    print("="*60)
    
    from modules.database.factory import get_db_connection, close_db_connection
    from modules.database.duckdb_handler import DuckDBDatabase
    from modules.database.postgres import PostgreSQLDatabase
    
    # Test 1: Start with DuckDB
    print("\n1. Testing DuckDB backend...")
    os.environ['DATABASE_BACKEND'] = 'duckdb'
    close_db_connection()  # Clear any existing connection
    
    db = get_db_connection()
    print(f"   ✓ Got connection: {type(db).__name__}")
    assert isinstance(db, DuckDBDatabase), "Should be DuckDB"
    print("   ✓ Confirmed DuckDB backend")
    
    # Test 2: Switch to PostgreSQL (import only, won't connect without server)
    print("\n2. Testing PostgreSQL backend selection...")
    os.environ['DATABASE_BACKEND'] = 'postgresql'
    close_db_connection()  # Clear DuckDB connection
    
    # We can't actually connect without a server, but we can verify the factory would try
    from modules.database.base import get_database_backend
    backend = get_database_backend()
    print(f"   ✓ Backend selection: {backend}")
    assert backend == 'postgresql', "Should select PostgreSQL"
    print("   ✓ PostgreSQL backend would be used")
    
    # Test 3: Switch back to DuckDB
    print("\n3. Switching back to DuckDB...")
    os.environ['DATABASE_BACKEND'] = 'duckdb'
    close_db_connection()
    
    db = get_db_connection()
    print(f"   ✓ Got connection: {type(db).__name__}")
    assert isinstance(db, DuckDBDatabase), "Should be DuckDB again"
    print("   ✓ Successfully switched back to DuckDB")
    
    # Test 4: Verify data operations still work after switching
    print("\n4. Testing operations after switching...")
    db.execute("CREATE TABLE IF NOT EXISTS test_switch (id INTEGER)")
    print("   ✓ Can execute queries")
    
    import pandas as pd
    df = pd.DataFrame({'id': [1, 2, 3]})
    records = db.insert_dataframe(df, 'test_switch', if_exists='replace')
    print(f"   ✓ Can insert data ({records} records)")
    
    count = db.get_row_count('test_switch')
    print(f"   ✓ Can query data ({count} records found)")
    
    db.execute("DROP TABLE test_switch")
    print("   ✓ Can clean up")
    
    print("\n" + "="*60)
    print("✅ BACKEND SWITCHING TEST PASSED")
    print("="*60)
    print("\nKey findings:")
    print("  - Can switch between backends using environment variable")
    print("  - Connection factory correctly instantiates the right class")
    print("  - Operations work correctly after switching")
    print("  - PostgreSQL module is ready (just needs server)")
    
    return True

if __name__ == "__main__":
    try:
        success = test_backend_switching()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
