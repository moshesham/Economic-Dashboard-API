"""
Initialize Database

Creates all tables and indexes for the Economic Dashboard.
Run this script once before using the database.
Supports both DuckDB and PostgreSQL.
"""

import sys
from pathlib import Path
import os

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from modules.database.factory import get_db_connection, get_backend
from modules.database.schema_generator import create_all_tables


def main():
    print("=" * 60)
    print("Economic Dashboard - Database Initialization")
    print("=" * 60)
    print()
    
    try:
        # Get database backend
        db_backend = get_backend()
        backend_name = db_backend.__class__.__name__
        print(f"Using database backend: {backend_name}")
        
        # Initialize database schema using unified schema generator
        print(f"Creating {backend_name} tables from SQLAlchemy models...")
        from modules.database.schema_generator import create_all_tables, set_schema_db, clear_schema_db
        set_schema_db(db_backend)
        try:
            create_all_tables()
        finally:
            clear_schema_db()
        
        # Verify tables were created
        print("\nVerifying database setup...")
        db = get_db_connection()
        
        if backend_name == 'PostgreSQLBackend':
            tables_query = """
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public'
                ORDER BY table_name
            """
            tables = db.query(tables_query)
            table_list = tables['table_name'].tolist()
        else:  # DuckDB
            tables_query = """
                SELECT name as table_name
                FROM sqlite_master 
                WHERE type='table' AND name NOT LIKE 'sqlite_%'
                ORDER BY name
            """
            tables = db.query(tables_query)
            table_list = tables['table_name'].tolist()
        
        print(f"\nFound {len(table_list)} tables:")
        for table in table_list:
            try:
                if backend_name == 'PostgreSQLBackend':
                    count_query = f"SELECT COUNT(*) as count FROM {table}"
                else:
                    count_query = f"SELECT COUNT(*) as count FROM {table}"
                count_result = db.query(count_query)
                count = count_result['count'].iloc[0]
                print(f"  • {table}: {count} records")
            except Exception as e:
                print(f"  • {table}: Error getting count - {e}")
        
        print("\n" + "=" * 60)
        print("Database initialization completed successfully!")
        print("=" * 60)
        print("\nNext steps:")
        print("1. Run 'python scripts/migrate_pickle_to_duckdb.py' to migrate existing data")
        print("2. Run your Streamlit app: 'streamlit run app.py'")
        
    except Exception as e:
        print(f"\n❌ Error during initialization: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
