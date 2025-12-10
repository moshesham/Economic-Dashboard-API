"""
Migrate Data from DuckDB/Pickle to PostgreSQL

Handles migration from existing DuckDB database or pickle files to PostgreSQL.
Supports both full migration and incremental updates.
"""

import sys
import os
from pathlib import Path
from datetime import datetime
import pandas as pd
from typing import Optional

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

# Set environment to use PostgreSQL for target
os.environ['DATABASE_BACKEND'] = 'postgresql'

from modules.database.factory import get_db_connection
from modules.database.duckdb_handler import DuckDBDatabase


def migrate_table(
    source_db: DuckDBDatabase,
    target_db,
    table_name: str,
    batch_size: int = 10000
) -> int:
    """
    Migrate a table from DuckDB to PostgreSQL in batches
    
    Args:
        source_db: Source DuckDB connection
        target_db: Target PostgreSQL connection
        table_name: Name of the table to migrate
        batch_size: Number of records per batch
    
    Returns:
        Total number of records migrated
    """
    print(f"\n{'='*60}")
    print(f"Migrating table: {table_name}")
    print(f"{'='*60}")
    
    try:
        # Get total count from source
        total_count = source_db.get_row_count(table_name)
        
        if total_count == 0:
            print(f"⚠️  No data found in {table_name}")
            return 0
        
        print(f"Found {total_count:,} records in source")
        
        # Migrate in batches
        migrated = 0
        offset = 0
        
        while offset < total_count:
            # Fetch batch from source
            query = f"SELECT * FROM {table_name} LIMIT {batch_size} OFFSET {offset}"
            batch_df = source_db.query(query)
            
            if batch_df.empty:
                break
            
            # Insert into target
            records_inserted = target_db.insert_dataframe(batch_df, table_name, if_exists="append")
            migrated += records_inserted
            offset += batch_size
            
            # Progress indicator
            progress = min(100, (offset / total_count) * 100)
            print(f"  Progress: {migrated:,}/{total_count:,} ({progress:.1f}%)")
        
        print(f"✓ Successfully migrated {migrated:,} records from {table_name}")
        return migrated
        
    except Exception as e:
        print(f"❌ Error migrating {table_name}: {e}")
        import traceback
        traceback.print_exc()
        return 0


def migrate_from_pickle():
    """
    Fallback: Migrate from pickle files if DuckDB is empty
    Uses the existing migrate_pickle_to_duckdb logic
    """
    print("\n" + "="*60)
    print("Checking for pickle cache files...")
    print("="*60)
    
    from scripts.migrate_pickle_to_duckdb import (
        migrate_fred_data,
        migrate_yfinance_data
    )
    
    fred_records = migrate_fred_data()
    yf_records = migrate_yfinance_data()
    
    return fred_records + yf_records


def verify_migration(db):
    """Verify the migration was successful"""
    print("\n" + "="*60)
    print("Verifying Migration")
    print("="*60)
    
    tables_to_check = [
        'fred_data',
        'yfinance_ohlcv',
        'cboe_vix_history',
        'ici_etf_weekly_flows',
        'news_sentiment',
        'technical_features',
        'options_data'
    ]
    
    total_records = 0
    
    for table in tables_to_check:
        try:
            count = db.get_row_count(table)
            total_records += count
            
            if count > 0:
                print(f"\n{table}:")
                print(f"  • Total records: {count:,}")
                
                # Get date range if applicable
                if 'date' in db.query(f"SELECT * FROM {table} LIMIT 1").columns:
                    stats = db.query(f"""
                        SELECT 
                            MIN(date) as earliest_date,
                            MAX(date) as latest_date
                        FROM {table}
                    """)
                    print(f"  • Date range: {stats['earliest_date'].iloc[0]} to {stats['latest_date'].iloc[0]}")
            else:
                print(f"\n{table}: No data")
                
        except Exception as e:
            print(f"\n{table}: Error checking ({str(e)})")
    
    return total_records


def main():
    print("="*60)
    print("Economic Dashboard - PostgreSQL Migration")
    print("="*60)
    print(f"Started at: {datetime.now()}")
    
    try:
        # Connect to source (DuckDB)
        print("\nConnecting to source DuckDB database...")
        source_db = DuckDBDatabase()
        
        # Connect to target (PostgreSQL)
        print("Connecting to target PostgreSQL database...")
        target_db = get_db_connection()
        
        print(f"Source: DuckDB at {source_db.db_path}")
        print(f"Target: PostgreSQL (DATABASE_URL from env)")
        
        # Tables to migrate
        tables = [
            'fred_data',
            'yfinance_ohlcv',
            'cboe_vix_history',
            'ici_etf_weekly_flows',
            'ici_etf_monthly_flows',
            'news_sentiment',
            'technical_features',
            'options_data',
            'ml_predictions',
            'model_performance',
            'data_refresh_log'
        ]
        
        total_migrated = 0
        
        for table in tables:
            try:
                migrated = migrate_table(source_db, target_db, table)
                total_migrated += migrated
            except Exception as e:
                print(f"⚠️  Skipping {table}: {str(e)}")
        
        # If no data was migrated from DuckDB, try pickle files
        if total_migrated == 0:
            print("\n⚠️  No data found in DuckDB. Checking pickle files...")
            pickle_records = migrate_from_pickle()
            total_migrated += pickle_records
        
        # Verify migration
        total_in_db = verify_migration(target_db)
        
        print("\n" + "="*60)
        print("Migration Summary")
        print("="*60)
        print(f"Records migrated: {total_migrated:,}")
        print(f"Total records in PostgreSQL: {total_in_db:,}")
        print("\n✅ Migration completed successfully!")
        print("="*60)
        
        print("\nNext steps:")
        print("1. Set DATABASE_BACKEND=postgresql in your .env file")
        print("2. Update docker-compose.yml to use PostgreSQL")
        print("3. Test the API and dashboard with PostgreSQL")
        print("4. Once verified, you can archive DuckDB files")
        
    except Exception as e:
        print(f"\n❌ Error during migration: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    
    finally:
        # Close connections
        if 'source_db' in locals():
            source_db.close()


if __name__ == "__main__":
    main()
