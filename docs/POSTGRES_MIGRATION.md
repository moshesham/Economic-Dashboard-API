# PostgreSQL Migration Guide

This guide covers the migration from DuckDB to PostgreSQL for the Economic Dashboard API.

## Overview

The database layer has been refactored to support both DuckDB (for local development) and PostgreSQL (for production). The implementation uses an abstract base class with concrete implementations for each database backend.

## Architecture

### New Files Created

1. **`modules/database/base.py`** - Abstract base class defining the database interface
2. **`modules/database/postgres.py`** - PostgreSQL implementation
3. **`modules/database/duckdb_handler.py`** - Refactored DuckDB implementation
4. **`modules/database/factory.py`** - Connection factory that returns the appropriate database instance
5. **`sql/init/01_schema.sql`** - PostgreSQL schema definition
6. **`scripts/migrate_to_postgres.py`** - Migration script

### Database Backend Selection

The database backend is controlled by the `DATABASE_BACKEND` environment variable:

```bash
# Use DuckDB (default for local development)
DATABASE_BACKEND=duckdb

# Use PostgreSQL (for production)
DATABASE_BACKEND=postgresql
```

## Migration Steps

### Step 1: Start PostgreSQL

Using Docker Compose:

```powershell
# Start only PostgreSQL
docker-compose up postgres

# Or start all services
docker-compose up
```

The PostgreSQL schema will be automatically initialized on first startup.

### Step 2: Set Environment Variables

Update your `.env` file:

```bash
# Database Configuration
DATABASE_BACKEND=postgresql
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=economic_dashboard
POSTGRES_USER=dashboard_user
POSTGRES_PASSWORD=dashboard_pass

# Or use a connection string
DATABASE_URL=postgresql://dashboard_user:dashboard_pass@localhost:5432/economic_dashboard
```

### Step 3: Run Migration Script

```powershell
# Run the migration script
python scripts/migrate_to_postgres.py
```

The script will:
1. Connect to your existing DuckDB database
2. Connect to PostgreSQL
3. Migrate all tables in batches
4. Verify the migration
5. Provide a summary

### Step 4: Update Application Configuration

Once migration is complete, update your application to use PostgreSQL:

```powershell
# In .env file
DATABASE_BACKEND=postgresql

# Restart services
docker-compose restart
```

### Step 5: Verify

Check that the API and dashboard work correctly:

```powershell
# Test API health
curl http://localhost:8000/health

# Check data endpoints
curl http://localhost:8000/v1/data/fred?series_id=GDP

# Test dashboard
# Open http://localhost:8501 in your browser
```

## Folder Structure Changes

New directories for better organization:

```
etl/
├── jobs/          # Scheduled data refresh jobs
├── sources/       # Data source modules (FRED, Yahoo Finance, etc.)
└── loaders/       # Data loading utilities

modules/
└── validation/    # Shared data validation logic

sql/
└── init/          # PostgreSQL initialization scripts
    └── 01_schema.sql
```

## Development Workflow

### Local Development (DuckDB)

```bash
DATABASE_BACKEND=duckdb
DUCKDB_PATH=data/duckdb/economic_dashboard.db
```

### Production (PostgreSQL)

```bash
DATABASE_BACKEND=postgresql
DATABASE_URL=postgresql://user:pass@host:5432/dbname
```

## Key Features

### 1. **Database Abstraction**
All database operations go through the abstract `BaseDatabase` interface, making it easy to switch between backends.

### 2. **Connection Pooling**
PostgreSQL connections use psycopg2 with proper connection management.

### 3. **Batch Inserts**
Efficient batch inserts using `execute_values` for PostgreSQL and native DataFrame support for DuckDB.

### 4. **Automatic Schema Management**
- PostgreSQL: Schema created via SQL files in `sql/init/`
- DuckDB: Schema created programmatically

### 5. **Conflict Handling**
PostgreSQL inserts use `ON CONFLICT DO NOTHING` to handle duplicate keys gracefully.

## Rollback Plan

If you need to rollback to DuckDB:

1. Set `DATABASE_BACKEND=duckdb` in `.env`
2. Restart services
3. Your DuckDB files remain untouched during migration

## Performance Considerations

### PostgreSQL Advantages
- Better for concurrent writes
- More robust for production workloads
- Better query optimization for complex joins
- ACID compliance
- Better backup/restore options

### DuckDB Advantages
- Faster for analytical queries
- No server setup required
- Better for local development
- Lower resource usage

## Troubleshooting

### Connection Issues

```python
# Test PostgreSQL connection
import psycopg2
conn = psycopg2.connect(
    host="localhost",
    port=5432,
    database="economic_dashboard",
    user="dashboard_user",
    password="dashboard_pass"
)
print("Connection successful!")
conn.close()
```

### Migration Failures

If migration fails midway:
1. PostgreSQL uses `ON CONFLICT DO NOTHING`, so re-running is safe
2. Check logs for specific error messages
3. Verify PostgreSQL is running: `docker-compose ps postgres`

### Schema Issues

To recreate the PostgreSQL schema:

```powershell
# Connect to PostgreSQL
docker-compose exec postgres psql -U dashboard_user -d economic_dashboard

# Drop all tables
DROP SCHEMA public CASCADE;
CREATE SCHEMA public;

# Exit and restart container to re-run init scripts
```

## Next Steps

1. **Phase 3**: Create API ingestion endpoints
2. **Phase 4**: Implement data validation layer
3. **Phase 5**: Optimize query performance
4. **Phase 6**: Set up automated backups

## Support

For issues or questions:
1. Check the logs: `docker-compose logs postgres`
2. Review the migration script output
3. Verify environment variables are set correctly
