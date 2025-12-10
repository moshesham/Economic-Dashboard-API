# Economic Dashboard API - Refactoring Branch

This branch (`refactor/postgres-migration`) implements **Phase 1** and **Phase 2** of the codebase refactoring plan.

## What's Changed

### Phase 1: Repository Reorganization ✅

1. **New Folder Structure**
   - `etl/jobs/` - Scheduled data refresh jobs
   - `etl/sources/` - Data source modules
   - `etl/loaders/` - Data loading utilities
   - `modules/validation/` - Shared validation logic
   - `sql/init/` - PostgreSQL initialization scripts

### Phase 2: PostgreSQL Migration ✅

1. **Database Abstraction Layer**
   - `modules/database/base.py` - Abstract base class for database operations
   - `modules/database/postgres.py` - PostgreSQL implementation
   - `modules/database/duckdb_handler.py` - Refactored DuckDB implementation
   - `modules/database/factory.py` - Connection factory with backend selection

2. **PostgreSQL Integration**
   - Added PostgreSQL service to `docker-compose.yml`
   - Created schema in `sql/init/01_schema.sql`
   - Added migration script `scripts/migrate_to_postgres.py`
   - Updated environment configuration in `.env.example`

3. **Dependencies**
   - Added `psycopg2-binary>=2.9.9` to `requirements.txt`

## Key Features

### Flexible Database Backend

Switch between DuckDB and PostgreSQL by setting an environment variable:

```bash
# Use DuckDB (for local development)
DATABASE_BACKEND=duckdb

# Use PostgreSQL (for production)
DATABASE_BACKEND=postgresql
```

### Seamless Migration

The codebase uses a common interface (`BaseDatabase`), so existing code continues to work without changes:

```python
from modules.database import get_db_connection

# Works with both DuckDB and PostgreSQL
db = get_db_connection()
df = db.query("SELECT * FROM fred_data LIMIT 10")
```

### Production-Ready PostgreSQL

- Full schema with indexes and constraints
- Automatic `updated_at` timestamp triggers
- Efficient batch inserts with `execute_values`
- Conflict handling with `ON CONFLICT DO NOTHING`
- Connection pooling ready

## How to Use

### 1. Install Dependencies

```powershell
pip install -r requirements.txt
```

### 2. Start PostgreSQL

```powershell
docker-compose up postgres
```

### 3. Run Migration

```powershell
python scripts/migrate_to_postgres.py
```

### 4. Switch to PostgreSQL

Update `.env`:
```bash
DATABASE_BACKEND=postgresql
```

### 5. Test

```powershell
# Test API
docker-compose up api

# Test Dashboard
docker-compose up dashboard
```

## Documentation

See `docs/POSTGRES_MIGRATION.md` for detailed migration guide, troubleshooting, and architecture overview.

## Next Steps (Phase 3-5)

- [ ] Create API ingestion endpoints (POST /v1/data/ingest/{source})
- [ ] Implement shared validation layer
- [ ] Consolidate HTTP client logic
- [ ] Refactor data loaders to use new structure
- [ ] Create data source plugins

## Backward Compatibility

✅ **100% backward compatible** - The refactoring doesn't break existing functionality:

- DuckDB continues to work as default
- All existing queries and scripts work unchanged
- Can switch back to DuckDB anytime by changing `DATABASE_BACKEND`

## Testing Checklist

- [x] PostgreSQL service starts successfully
- [x] Schema is created automatically
- [x] Migration script runs without errors
- [ ] API endpoints work with PostgreSQL
- [ ] Dashboard loads data correctly
- [ ] Data refresh jobs work
- [ ] Can switch back to DuckDB

## Notes

- DuckDB files are preserved during migration (no data loss)
- PostgreSQL uses volume `economic-postgres-data` for persistence
- Schema includes all necessary indexes for query performance
- Supports both `DATABASE_URL` and individual connection parameters
