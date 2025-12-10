# Quick Start Guide - PostgreSQL Migration

## 🚀 Getting Started

### Option 1: Use PostgreSQL (Recommended for Production)

```powershell
# 1. Start PostgreSQL
docker-compose up -d postgres

# 2. Wait for PostgreSQL to be healthy
docker-compose ps postgres

# 3. Run migration
python scripts/migrate_to_postgres.py

# 4. Update .env
# DATABASE_BACKEND=postgresql

# 5. Start all services
docker-compose up
```

### Option 2: Continue with DuckDB (Local Development)

```powershell
# 1. Ensure .env has:
# DATABASE_BACKEND=duckdb

# 2. Start services
docker-compose up

# Nothing else needed - works as before!
```

## 📋 Common Commands

### Check Database Connection

```python
from modules.database import get_db_connection

db = get_db_connection()
print(f"Using: {type(db).__name__}")
# Output: PostgreSQLDatabase or DuckDBDatabase
```

### Query Data

```python
from modules.database import get_db_connection

db = get_db_connection()

# Query FRED data
fred_df = db.query("""
    SELECT series_id, date, value 
    FROM fred_data 
    WHERE series_id = 'GDP' 
    ORDER BY date DESC 
    LIMIT 10
""")

print(fred_df)
```

### Insert Data

```python
import pandas as pd
from modules.database import get_db_connection

db = get_db_connection()

# Create sample data
df = pd.DataFrame({
    'series_id': ['TEST1', 'TEST2'],
    'date': ['2024-01-01', '2024-01-02'],
    'value': [100.0, 200.0]
})

# Insert
records = db.insert_dataframe(df, 'fred_data', if_exists='append')
print(f"Inserted {records} records")
```

## 🔧 Troubleshooting

### PostgreSQL won't start

```powershell
# Check logs
docker-compose logs postgres

# Restart
docker-compose restart postgres

# Nuclear option - delete and recreate
docker-compose down -v
docker-compose up postgres
```

### Migration fails

```powershell
# Re-run is safe (uses ON CONFLICT DO NOTHING)
python scripts/migrate_to_postgres.py

# Check PostgreSQL is running
docker-compose ps postgres

# Verify connection
docker-compose exec postgres psql -U dashboard_user -d economic_dashboard -c "\dt"
```

### Connection errors

```powershell
# Check environment variables
cat .env | grep DATABASE

# Test connection directly
docker-compose exec postgres psql -U dashboard_user -d economic_dashboard
```

## 📊 Verify Migration

### Check record counts

```powershell
docker-compose exec postgres psql -U dashboard_user -d economic_dashboard

# In PostgreSQL prompt:
SELECT 
    'fred_data' as table_name, 
    COUNT(*) as records 
FROM fred_data
UNION ALL
SELECT 
    'yfinance_ohlcv', 
    COUNT(*) 
FROM yfinance_ohlcv;
```

### Compare with DuckDB

```python
from modules.database.duckdb_handler import DuckDBDatabase
from modules.database.postgres import PostgreSQLDatabase

# DuckDB
duck_db = DuckDBDatabase()
duck_count = duck_db.get_row_count('fred_data')
print(f"DuckDB: {duck_count} records")

# PostgreSQL
pg_db = PostgreSQLDatabase()
pg_count = pg_db.get_row_count('fred_data')
print(f"PostgreSQL: {pg_count} records")
```

## 🎯 Testing the API

### Start API with PostgreSQL

```powershell
# Set environment
$env:DATABASE_BACKEND="postgresql"

# Start API
docker-compose up api

# Test endpoint
curl http://localhost:8000/health
curl http://localhost:8000/v1/data/fred?series_id=GDP
```

### Start Dashboard

```powershell
# Start with dashboard profile
docker-compose --profile with-dashboard up

# Visit http://localhost:8501
```

## 🔄 Switch Between Databases

### Switch to PostgreSQL

```powershell
# Update .env
DATABASE_BACKEND=postgresql

# Restart
docker-compose restart
```

### Switch back to DuckDB

```powershell
# Update .env
DATABASE_BACKEND=duckdb

# Restart
docker-compose restart
```

## 📦 Environment Variables Reference

```bash
# Database backend selection
DATABASE_BACKEND=duckdb  # or postgresql

# PostgreSQL (when DATABASE_BACKEND=postgresql)
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=economic_dashboard
POSTGRES_USER=dashboard_user
POSTGRES_PASSWORD=dashboard_pass

# Or use connection string
DATABASE_URL=postgresql://user:pass@host:5432/dbname

# DuckDB (when DATABASE_BACKEND=duckdb)
DUCKDB_PATH=data/duckdb/economic_dashboard.db
```

## 🔍 Useful SQL Queries

### Check latest data

```sql
-- Latest FRED data
SELECT series_id, MAX(date) as latest_date
FROM fred_data
GROUP BY series_id
ORDER BY latest_date DESC;

-- Latest stock data
SELECT ticker, MAX(date) as latest_date
FROM yfinance_ohlcv
GROUP BY ticker;
```

### Check data freshness

```sql
SELECT 
    data_type,
    MAX(refresh_time) as last_refresh,
    status
FROM data_refresh_log
GROUP BY data_type, status
ORDER BY last_refresh DESC;
```

### Table sizes

```sql
SELECT 
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
```

## 📚 Next Steps

1. **Test the migration**: Run through the verification steps
2. **Update your workflow**: Switch to PostgreSQL for production
3. **Monitor performance**: Compare query times between backends
4. **Plan Phase 3**: API ingestion endpoints
5. **Review docs**: Read `docs/POSTGRES_MIGRATION.md` for details

## 🆘 Get Help

- Check logs: `docker-compose logs [service]`
- Read docs: `docs/POSTGRES_MIGRATION.md`
- View summary: `docs/PHASE_1_2_SUMMARY.md`
- Check branch readme: `BRANCH_README.md`
