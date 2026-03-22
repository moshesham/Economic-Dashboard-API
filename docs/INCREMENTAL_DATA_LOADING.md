# Economic Dashboard API — Incremental Data Loading

## Problem it Solves

The original data refresh always performed a **full historical reload**
(20 years of data on every run).  This is expensive in time, API quota,
and memory for large series catalogs.

## Solution: Watermark-Based Incremental Loading

Each (source, series_key) pair stores a **high-water mark** in the
`data_ingestion_watermarks` database table — the latest date that was
successfully fetched.  On subsequent runs only records *after* that date
are requested from the upstream API.

## Files Added / Modified

| File | Change |
|------|--------|
| `modules/database/models.py` | ➕ `DataIngestionWatermark` ORM model |
| `modules/ingestion/__init__.py` | ➕ New package |
| `modules/ingestion/incremental_fetcher.py` | ➕ `IncrementalFetcher` class |
| `scripts/refresh_data_smart.py` | ✏️ Added `--incremental` flag + `run_incremental_refresh()` |
| `airflow/dags/economic_data_refresh_dag.py` | ✏️ Added `incremental_data_refresh` task |
| `alembic/versions/a1b2c3d4e5f6_*.py` | ➕ Alembic migration |

## Usage

### One-off incremental refresh (all configured series)
```bash
python scripts/refresh_data_smart.py --incremental
```

### Limit to specific series
```bash
python scripts/refresh_data_smart.py --incremental --series UNRATE CPIAUCSL DGS10
```

### In Python code
```python
from modules.ingestion import get_incremental_fetcher

fetcher = get_incremental_fetcher()

# Single FRED series (only fetches new data)
df = fetcher.fetch_fred_incremental("UNRATE")

# Batch FRED
combined_df = fetcher.fetch_fred_batch_incremental({
    "Unemployment": "UNRATE",
    "CPI": "CPIAUCSL",
})

# Yahoo Finance ticker
ohlcv = fetcher.fetch_yfinance_incremental("^GSPC")

# Check watermark status
print(fetcher.get_all_watermarks())

# Find stale series (> 1 day old)
stale = fetcher.get_stale_series(max_age_days=1)
```

## Database Schema

```sql
CREATE TABLE data_ingestion_watermarks (
    source            VARCHAR NOT NULL,    -- 'fred', 'yfinance', 'bls', ...
    series_key        VARCHAR NOT NULL,    -- 'UNRATE', '^GSPC', ...
    last_fetched_date DATE    NOT NULL,    -- High-water mark
    last_run_at       DATETIME,           -- Wall-clock time of last run
    records_fetched   INTEGER DEFAULT 0,
    status            VARCHAR DEFAULT 'ok',      -- 'ok' | 'error'
    error_message     VARCHAR,
    PRIMARY KEY (source, series_key)
);
```

## First Run vs. Subsequent Runs

| Run | Behaviour |
|-----|-----------|
| First run (no watermark) | Fetches full history (`default_start_date`, default `2000-01-01`) |
| Subsequent runs | Fetches only `watermark_date + 1 day → today` |
| After an error | Error is recorded in table; next run retries from last good watermark |

## Airflow Integration

The `economic_dashboard_data_refresh` DAG now includes a new
`incremental_data_refresh` task that runs `--incremental` before the
legacy full-refresh task.
