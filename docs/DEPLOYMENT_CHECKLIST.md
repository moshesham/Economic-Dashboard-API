# Production Deployment Checklist

This checklist guides you through deploying the refactored Economic Dashboard API to production with PostgreSQL.

## Pre-Deployment

### 1. Environment Setup

- [ ] Create production `.env` file:
  ```bash
  cp .env.example .env
  ```

- [ ] Configure database backend:
  ```env
  DATABASE_BACKEND=postgresql
  DATABASE_URL=postgresql://user:password@host:5432/database
  # Or individual components:
  POSTGRES_HOST=localhost
  POSTGRES_PORT=5432
  POSTGRES_DB=economic_dashboard
  POSTGRES_USER=dashboard_user
  POSTGRES_PASSWORD=<strong-password>
  ```

- [ ] Add API keys:
  ```env
  FRED_API_KEY=your_key_here
  NEWS_API_KEY=your_key_here
  ALPHA_VANTAGE_API_KEY=your_key_here
  ```

- [ ] Configure Redis (for API caching):
  ```env
  REDIS_URL=redis://redis:6379/0
  ```

### 2. Database Migration

- [ ] Start PostgreSQL service:
  ```bash
  docker-compose up -d postgres
  ```

- [ ] Verify PostgreSQL is running:
  ```bash
  docker-compose ps postgres
  docker-compose logs postgres
  ```

- [ ] Test connection:
  ```python
  from modules.database import get_db_connection
  db = get_db_connection()
  print(f"Connected to: {type(db._backend).__name__}")
  ```

- [ ] Initialize schema (automatic on first connection):
  ```python
  from modules.database import init_database
  init_database()
  ```

- [ ] **If migrating from DuckDB**, run migration script:
  ```bash
  python scripts/migrate_pickle_to_duckdb.py  # If needed
  # Then export from DuckDB and import to PostgreSQL
  # (Create custom migration script or use SQL COPY)
  ```

### 3. GitHub Actions Secrets

- [ ] Add secrets to GitHub repository:
  - `DATABASE_URL` - PostgreSQL connection string
  - `FRED_API_KEY`
  - `NEWS_API_KEY`
  - `ALPHA_VANTAGE_API_KEY`

- [ ] Update workflow files to use PostgreSQL:
  ```yaml
  env:
    DATABASE_BACKEND: postgresql
    DATABASE_URL: ${{ secrets.DATABASE_URL }}
  ```

## Deployment

### Option A: Docker Compose (Recommended)

- [ ] Build images:
  ```bash
  docker-compose build
  ```

- [ ] Start all services:
  ```bash
  docker-compose up -d
  ```

- [ ] Verify services are running:
  ```bash
  docker-compose ps
  ```

- [ ] Check logs:
  ```bash
  docker-compose logs -f api
  docker-compose logs -f worker
  docker-compose logs -f postgres
  ```

- [ ] Test API health:
  ```bash
  curl http://localhost:8000/health
  ```

- [ ] Test database connection:
  ```bash
  curl http://localhost:8000/v1/data/health
  ```

### Option B: Manual Deployment

- [ ] Install dependencies:
  ```bash
  pip install -r requirements.txt
  ```

- [ ] Start PostgreSQL (external):
  ```bash
  # Ensure PostgreSQL is running and accessible
  ```

- [ ] Start API server:
  ```bash
  uvicorn api.main:app --host 0.0.0.0 --port 8000 --workers 4
  ```

- [ ] Start background worker:
  ```bash
  python worker.py
  ```

## Post-Deployment Verification

### 1. API Endpoints

- [ ] Health check:
  ```bash
  curl http://localhost:8000/health
  ```

- [ ] API documentation:
  ```bash
  open http://localhost:8000/docs
  ```

- [ ] Test data endpoint:
  ```bash
  curl http://localhost:8000/v1/data/fred?series_ids=GDP
  ```

- [ ] Test ingestion endpoint (requires API key):
  ```bash
  curl -X POST http://localhost:8000/v1/ingest/fred \
    -H "X-API-Key: your-api-key" \
    -H "Content-Type: application/json" \
    -d '[{"series_id":"GDP","date":"2024-01-01","value":21000}]'
  ```

### 2. Database Verification

- [ ] Connect to PostgreSQL:
  ```bash
  docker-compose exec postgres psql -U dashboard_user -d economic_dashboard
  ```

- [ ] Check tables exist:
  ```sql
  \dt
  ```

- [ ] Verify data:
  ```sql
  SELECT COUNT(*) FROM fred_data;
  SELECT COUNT(*) FROM yfinance_ohlcv;
  ```

- [ ] Check indexes:
  ```sql
  \di
  ```

### 3. Data Refresh Jobs

- [ ] Trigger manual refresh:
  ```bash
  # Via GitHub Actions UI: Actions → Data Refresh → Run workflow
  # Or manually:
  python -c "from etl.sources.fred import refresh_fred_data; refresh_fred_data()"
  ```

- [ ] Verify data was inserted:
  ```sql
  SELECT 
    MAX(created_at) as last_insert,
    COUNT(*) as total_records
  FROM fred_data;
  ```

- [ ] Check data refresh logs:
  ```sql
  SELECT * FROM data_refresh_log 
  ORDER BY start_time DESC 
  LIMIT 10;
  ```

### 4. Performance Testing

- [ ] Run load test on API:
  ```bash
  # Using Apache Bench
  ab -n 1000 -c 10 http://localhost:8000/v1/data/fred?series_ids=GDP
  ```

- [ ] Monitor database connections:
  ```sql
  SELECT count(*) FROM pg_stat_activity 
  WHERE datname = 'economic_dashboard';
  ```

- [ ] Check API response times:
  ```bash
  curl -w "@curl-format.txt" -o /dev/null -s http://localhost:8000/v1/data/fred?series_ids=GDP
  ```

## Monitoring Setup

### 1. Logging

- [ ] Configure log aggregation:
  ```yaml
  # docker-compose.yml
  logging:
    driver: "json-file"
    options:
      max-size: "10m"
      max-file: "3"
  ```

- [ ] Set up log rotation:
  ```bash
  # In cron
  0 0 * * * find /var/log/economic-dashboard -name "*.log" -mtime +7 -delete
  ```

### 2. Metrics

- [ ] Enable PostgreSQL query logging:
  ```sql
  ALTER SYSTEM SET log_min_duration_statement = 1000; -- Log queries > 1s
  SELECT pg_reload_conf();
  ```

- [ ] Monitor API metrics:
  ```python
  # Add to api/main.py
  from prometheus_fastapi_instrumentator import Instrumentator
  Instrumentator().instrument(app).expose(app)
  ```

### 3. Alerts

- [ ] Set up disk space alerts (PostgreSQL data volume)
- [ ] Set up API uptime monitoring (e.g., UptimeRobot)
- [ ] Set up data freshness alerts (SLA breaches)

## Backup & Recovery

### 1. Database Backups

- [ ] Set up automated PostgreSQL backups:
  ```bash
  # Daily backup cron job
  0 2 * * * docker-compose exec -T postgres pg_dump -U dashboard_user economic_dashboard | gzip > /backups/db-$(date +\%Y\%m\%d).sql.gz
  ```

- [ ] Test restore:
  ```bash
  gunzip < /backups/db-20241210.sql.gz | docker-compose exec -T postgres psql -U dashboard_user economic_dashboard
  ```

- [ ] Set up offsite backup (S3, Google Drive, etc.)

### 2. Configuration Backups

- [ ] Backup `.env` file (securely)
- [ ] Backup `docker-compose.yml`
- [ ] Document all GitHub secrets

## Security Hardening

### 1. Database Security

- [ ] Change default PostgreSQL password:
  ```sql
  ALTER USER dashboard_user WITH PASSWORD 'new-strong-password';
  ```

- [ ] Restrict PostgreSQL network access:
  ```yaml
  # docker-compose.yml
  postgres:
    ports:
      - "127.0.0.1:5432:5432"  # Only localhost
  ```

- [ ] Enable SSL for PostgreSQL connections:
  ```env
  DATABASE_URL=postgresql://user:pass@host:5432/db?sslmode=require
  ```

### 2. API Security

- [ ] Enable API key authentication:
  ```env
  API_KEY_ENABLED=true
  API_SECRET_KEY=<generate-random-key>
  ```

- [ ] Set up rate limiting:
  ```env
  API_RATE_LIMIT=100  # requests per minute
  ```

- [ ] Configure CORS properly:
  ```python
  # api/main.py
  app.add_middleware(
      CORSMiddleware,
      allow_origins=["https://yourdomain.com"],  # Not "*"
      allow_credentials=True,
      allow_methods=["GET", "POST"],
      allow_headers=["*"],
  )
  ```

### 3. Container Security

- [ ] Run containers as non-root:
  ```dockerfile
  USER nobody
  ```

- [ ] Scan images for vulnerabilities:
  ```bash
  docker scan economic-api:latest
  ```

- [ ] Keep base images updated:
  ```dockerfile
  FROM python:3.11-slim  # Use specific versions
  ```

## Rollback Plan

If issues arise after deployment:

1. **Revert to DuckDB:**
   ```env
   DATABASE_BACKEND=duckdb
   DUCKDB_PATH=./data/duckdb/economic_dashboard.duckdb
   ```

2. **Restore previous Docker images:**
   ```bash
   docker-compose down
   git checkout <previous-commit>
   docker-compose build
   docker-compose up -d
   ```

3. **Restore database from backup:**
   ```bash
   gunzip < /backups/db-20241209.sql.gz | docker-compose exec -T postgres psql -U dashboard_user economic_dashboard
   ```

## Troubleshooting

### API won't start
```bash
# Check logs
docker-compose logs api

# Common issues:
# - Missing environment variables
# - Database connection failed
# - Port already in use
```

### Database connection errors
```bash
# Check PostgreSQL is running
docker-compose ps postgres

# Check connection string
echo $DATABASE_URL

# Test connection manually
docker-compose exec postgres psql -U dashboard_user economic_dashboard
```

### Data not refreshing
```bash
# Check GitHub Actions logs
# Check worker logs
docker-compose logs worker

# Manually trigger refresh
python -c "from etl.sources.fred import refresh_fred_data; refresh_fred_data()"
```

## Success Criteria

- [ ] All services running (postgres, api, worker, redis)
- [ ] API health endpoint returns 200 OK
- [ ] Database contains recent data (check `created_at` timestamps)
- [ ] Scheduled jobs running successfully (check GitHub Actions)
- [ ] API documentation accessible at `/docs`
- [ ] No errors in application logs
- [ ] Response times < 200ms for simple queries
- [ ] Backup system operational

---

**Deployment Complete!** 🎉

Monitor the system for the first 24 hours and verify scheduled jobs run successfully.
