# Quick Reference Guide - Refactored Architecture

## Common Tasks

### Get Database Connection
```python
from modules.database import get_db_connection

db = get_db_connection()  # Auto-selects DuckDB or PostgreSQL
df = db.query("SELECT * FROM fred_data LIMIT 10")
```

### Insert Data
```python
from modules.database.queries import insert_fred_data, insert_stock_data
import pandas as pd

# FRED data
df_fred = pd.DataFrame({
    'series_id': ['GDP', 'CPI'],
    'date': ['2024-01-01', '2024-01-01'],
    'value': [21000, 300]
})
insert_fred_data(df_fred)

# Stock data
df_stock = pd.DataFrame({
    'ticker': ['AAPL'],
    'date': ['2024-01-01'],
    'close': [150.0],
    'volume': [1000000]
})
insert_stock_data(df_stock)
```

### Validate Data
```python
from modules.validation import validate_and_clean

validated_df = validate_and_clean(df, 'fred', raise_errors=True)
```

### Fetch from External API
```python
from modules.http_client import create_client
import os

# FRED
client = create_client('fred', api_key=os.getenv('FRED_API_KEY'))
data = client.get_json('series/observations', params={'series_id': 'GDP'})

# Yahoo Finance
client = create_client('yahoo')
response = client.get('https://query1.finance.yahoo.com/v7/finance/quote?symbols=AAPL')
```

### Register New Data Source
```python
from modules.data_sources import register_source, DataSourceConfig, DataFrequency, DataSourceType
from datetime import timedelta

register_source(DataSourceConfig(
    source_id='my_source',
    source_name='My Data Source',
    source_type=DataSourceType.API,
    frequency=DataFrequency.DAILY,
    sla=timedelta(hours=6),
    fetch_function='etl.sources.my_source.fetch_data',
    table_name='my_source_data',
    validation_type='my_source',
    cron_schedule='0 6 * * *',
))
```

### List All Data Sources
```python
from modules.data_sources import list_sources, DataFrequency

# All sources
all_sources = list_sources()

# Daily sources only
daily_sources = list_sources(frequency=DataFrequency.DAILY)

# Enabled sources
enabled = list_sources(enabled=True)
```

## File Locations

### Core Modules
- `modules/database/factory.py` - Database connection factory
- `modules/database/queries.py` - Pre-built queries
- `modules/database/schema.py` - DuckDB schema
- `modules/database/postgres_schema.py` - PostgreSQL schema
- `modules/http_client.py` - HTTP client base class
- `modules/validation.py` - Data validation schemas
- `modules/data_sources.py` - Data source registry

### ETL
- `etl/sources/` - Individual data source fetch modules
- `etl/loaders/` - Data loading utilities
- `etl/jobs/` - Scheduled job definitions

### API
- `api/main.py` - FastAPI application
- `api/v1/routes/data.py` - Data retrieval endpoints
- `api/v1/routes/ingest.py` - Data ingestion endpoints
- `api/v1/routes/health.py` - Health check
- `api/v1/dependencies/auth.py` - Authentication

### Configuration
- `.env` - Environment configuration
- `docker-compose.yml` - Docker services
- `requirements.txt` - Python dependencies

### Documentation
- `docs/ADDING_DATA_SOURCES.md` - How to add new data sources
- `docs/REFACTOR_SUMMARY.md` - Implementation summary
- `docs/DEPLOYMENT_CHECKLIST.md` - Production deployment guide

## Environment Variables

### Database
```env
DATABASE_BACKEND=postgresql  # or 'duckdb'
DATABASE_URL=postgresql://user:pass@host:5432/db
```

### API Keys
```env
FRED_API_KEY=your_key
NEWS_API_KEY=your_key
ALPHA_VANTAGE_API_KEY=your_key
```

### API Settings
```env
API_KEY_ENABLED=true
API_SECRET_KEY=your_secret
API_RATE_LIMIT=100
```

## API Endpoints

### Health
- `GET /health` - API health status

### Data Retrieval
- `GET /v1/data/fred` - Get FRED series
- `GET /v1/data/stock` - Get stock OHLCV
- `GET /v1/data/options` - Get options data

### Data Ingestion (Auth Required)
- `POST /v1/ingest/fred` - Ingest FRED data (JSON)
- `POST /v1/ingest/stock` - Ingest stock data (JSON)
- `POST /v1/ingest/csv/{data_type}` - Upload CSV file
- `POST /v1/ingest/bulk/{data_type}` - Bulk background ingestion
- `GET /v1/ingest/status/{job_id}` - Check background job status

## Database Tables

### Core Data
- `fred_data` - Economic indicators from FRED
- `yfinance_ohlcv` - Stock price data
- `options_data` - Options metrics
- `cboe_vix_history` - VIX historical data
- `ici_etf_weekly_flows` - ETF flow statistics

### Features
- `technical_features` - RSI, MACD, Bollinger Bands, etc.
- `derived_features` - Cross-asset features, regime detection

### ML
- `ml_predictions` - Model predictions
- `model_performance` - Backtest metrics
- `feature_importance` - Feature importance tracking

### System
- `data_refresh_log` - ETL job tracking
- `data_retention_policy` - Retention rules

## Docker Commands

### Start all services
```bash
docker-compose up -d
```

### View logs
```bash
docker-compose logs -f api
docker-compose logs -f postgres
docker-compose logs -f worker
```

### Rebuild after code changes
```bash
docker-compose build api
docker-compose restart api
```

### Access PostgreSQL
```bash
docker-compose exec postgres psql -U dashboard_user economic_dashboard
```

### Stop all services
```bash
docker-compose down
```

## Validation Schemas

Available validation types in `modules/validation.py`:
- `fred` - FRED data
- `stock` / `stock_ohlcv` / `yfinance` - Stock OHLCV
- `options` - Options data
- `ici_weekly` - ICI weekly flows
- `cboe_vix` - CBOE VIX data
- `technical_features` - Technical indicators
- `ml_predictions` - ML predictions
- `sec_filings` - SEC filings

## HTTP Clients

Available clients in `modules/http_client.py`:
- `FREDClient` - Federal Reserve Economic Data
- `YahooFinanceClient` - Yahoo Finance
- `CBOEClient` - Chicago Board Options Exchange
- `ICIClient` - Investment Company Institute
- `NewsAPIClient` - News API

Create with factory:
```python
from modules.http_client import create_client

client = create_client('fred', api_key='your_key')
```

## Testing

### Test database connection
```python
from modules.database import get_db_connection
db = get_db_connection()
print(f"Backend: {type(db._backend).__name__}")
```

### Test API locally
```bash
uvicorn api.main:app --reload
# Open http://localhost:8000/docs
```

### Run tests
```bash
pytest tests/
```

## Troubleshooting

### Database connection failed
```python
import os
print(f"Backend: {os.getenv('DATABASE_BACKEND', 'duckdb')}")
print(f"URL: {os.getenv('DATABASE_URL', 'Not set')}")
```

### Validation errors
```python
from modules.validation import get_validator

validator = get_validator('fred')
try:
    validated = validator.validate(df, raise_errors=True)
except Exception as e:
    print(f"Validation failed: {e}")
```

### API key issues
```python
import os
print(f"FRED: {'✓' if os.getenv('FRED_API_KEY') else '✗'}")
print(f"NEWS: {'✓' if os.getenv('NEWS_API_KEY') else '✗'}")
```

## Data Source SLAs

Default SLAs configured in `modules/data_sources.py`:
- **Daily data**: 6 hours
- **Weekly data**: 1 day
- **Monthly data**: 7 days
- **Quarterly data**: 30 days

Check if data is stale:
```python
from modules.data_sources import get_source
from datetime import datetime

source = get_source('fred_gdp')
last_update = datetime(2024, 1, 1)
is_stale = source.is_stale(last_update)
print(f"Data stale: {is_stale}")
```

## Rate Limits

Default rate limits:
- FRED: 120 calls/minute
- Yahoo Finance: 2000 calls/hour
- CBOE: 60 calls/minute
- ICI: 30 calls/minute
- News API: 100 calls/day (free tier)

Override in client:
```python
client = BaseAPIClient(
    base_url='https://api.example.com',
    rate_limit=(200, 60)  # 200 calls per minute
)
```

## Useful SQL Queries

### Check data freshness
```sql
SELECT 
    'fred_data' as table_name,
    COUNT(*) as total_records,
    MAX(created_at) as last_insert
FROM fred_data

UNION ALL

SELECT 
    'yfinance_ohlcv',
    COUNT(*),
    MAX(created_at)
FROM yfinance_ohlcv;
```

### Find missing dates
```sql
WITH date_series AS (
    SELECT generate_series(
        '2024-01-01'::date,
        CURRENT_DATE,
        '1 day'::interval
    )::date as date
)
SELECT ds.date
FROM date_series ds
LEFT JOIN yfinance_ohlcv yf 
    ON ds.date = yf.date 
    AND yf.ticker = 'SPY'
WHERE yf.date IS NULL
ORDER BY ds.date;
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

---

**For detailed guides, see:**
- Adding data sources: `docs/ADDING_DATA_SOURCES.md`
- Deployment: `docs/DEPLOYMENT_CHECKLIST.md`
- Architecture: `docs/REFACTOR_SUMMARY.md`
