# Adding New Data Sources

This guide explains how to add a new data source to the Economic Dashboard API using the extensibility framework.

## Table of Contents

1. [Quick Start](#quick-start)
2. [5-Step Checklist](#5-step-checklist)
3. [Detailed Guide](#detailed-guide)
4. [Examples](#examples)
5. [Best Practices](#best-practices)

## Quick Start

Adding a new data source involves 5 simple steps:

1. **Define Source Config** - Register in `modules/data_sources.py`
2. **Create Fetch Module** - Add `etl/sources/{source_name}.py`
3. **Add DB Schema** - Update `modules/database/postgres_schema.py` (or `schema.py` for DuckDB)
4. **Register Scheduler** - Add to GitHub workflow or `services/scheduler.py`
5. **Expose via API** - Add read endpoint to `api/v1/routes/data.py`

## 5-Step Checklist

### Step 1: Define Source Configuration

Add a new `DataSourceConfig` in `modules/data_sources.py`:

```python
from modules.data_sources import register_source, DataSourceConfig, DataFrequency, DataSourceType
from datetime import timedelta

register_source(DataSourceConfig(
    source_id='my_new_source',
    source_name='My New Data Source',
    source_type=DataSourceType.API,  # or FILE_DOWNLOAD, WEB_SCRAPE
    frequency=DataFrequency.DAILY,
    sla=timedelta(hours=6),  # Max data staleness
    
    # Fetch configuration
    fetch_function='etl.sources.my_source.fetch_data',
    fetch_params={'param1': 'value1'},
    
    # Storage configuration
    table_name='my_source_data',
    validation_type='my_source',
    
    # Optional: API settings
    requires_api_key=True,
    api_key_env_var='MY_SOURCE_API_KEY',
    rate_limit=(100, 60),  # 100 calls per minute
    
    # Optional: Schedule
    cron_schedule='0 6 * * *',  # Daily at 6 AM
    
    # Metadata
    description='Description of the data source',
    tags=['category1', 'category2'],
))
```

### Step 2: Create Fetch Module

Create `etl/sources/my_source.py`:

```python
"""
My New Data Source

Fetches data from XYZ API/Website.
"""

import pandas as pd
import logging
from modules.http_client import BaseAPIClient, create_client
from modules.validation import validate_and_clean

logger = logging.getLogger(__name__)


def fetch_data(param1: str, start_date: str = None, end_date: str = None) -> pd.DataFrame:
    """
    Fetch data from My Source.
    
    Args:
        param1: Parameter description
        start_date: Optional start date (YYYY-MM-DD)
        end_date: Optional end date (YYYY-MM-DD)
        
    Returns:
        DataFrame with standardized columns
    """
    logger.info(f"Fetching data from My Source: {param1}")
    
    # Option 1: Use existing client
    client = create_client('my_source', api_key=os.getenv('MY_SOURCE_API_KEY'))
    
    # Option 2: Create custom client
    # client = BaseAPIClient(
    #     base_url='https://api.mysource.com',
    #     api_key=os.getenv('MY_SOURCE_API_KEY'),
    #     rate_limit=(100, 60)
    # )
    
    try:
        # Make API request
        data = client.get_json('/endpoint', params={'param1': param1})
        
        # Convert to DataFrame
        df = pd.DataFrame(data['results'])
        
        # Standardize column names
        df = df.rename(columns={
            'old_column': 'new_column',
            'date_col': 'date',
        })
        
        # Ensure required columns exist
        df['source'] = 'my_source'
        
        # Validate
        validated_df = validate_and_clean(df, 'my_source', raise_errors=True)
        
        logger.info(f"Fetched {len(validated_df)} records from My Source")
        return validated_df
        
    except Exception as e:
        logger.error(f"Error fetching data from My Source: {e}")
        raise
    finally:
        client.close()


def refresh_my_source_data():
    """
    Refresh My Source data in the database.
    
    This is the main entry point called by schedulers.
    """
    from modules.database.queries import insert_generic_data
    from datetime import datetime, timedelta
    
    # Fetch data for last 30 days
    end_date = datetime.now().strftime('%Y-%m-%d')
    start_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
    
    df = fetch_data(
        param1='default_value',
        start_date=start_date,
        end_date=end_date
    )
    
    if not df.empty:
        records_inserted = insert_generic_data(df, 'my_source_data')
        logger.info(f"Inserted {records_inserted} records into my_source_data")
        return records_inserted
    
    return 0
```

### Step 3: Add Database Schema

#### For PostgreSQL (`modules/database/postgres_schema.py`):

```python
def create_my_source_table(db):
    """Create table for My Source data."""
    db.execute("""
        CREATE TABLE IF NOT EXISTS my_source_data (
            id SERIAL PRIMARY KEY,
            date DATE NOT NULL,
            metric_name VARCHAR(100) NOT NULL,
            value DOUBLE PRECISION,
            metadata JSONB,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE (date, metric_name)
        )
    """)
    
    db.execute("CREATE INDEX IF NOT EXISTS idx_my_source_date ON my_source_data(date)")
    db.execute("CREATE INDEX IF NOT EXISTS idx_my_source_metric ON my_source_data(metric_name)")
    logger.info("Created table: my_source_data")

# Add to create_all_tables() function:
def create_all_tables(db):
    # ... existing tables ...
    create_my_source_table(db)
```

#### For DuckDB (`modules/database/schema.py`):

```python
def create_my_source_table():
    """Create table for My Source data."""
    db = get_db_connection()
    db.execute("""
        CREATE TABLE IF NOT EXISTS my_source_data (
            date DATE NOT NULL,
            metric_name VARCHAR NOT NULL,
            value DOUBLE,
            metadata VARCHAR,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (date, metric_name)
        )
    """)
    
    db.execute("CREATE INDEX IF NOT EXISTS idx_my_source_date ON my_source_data(date)")
    db.execute("CREATE INDEX IF NOT EXISTS idx_my_source_metric ON my_source_data(metric_name)")

# Add to create_all_tables() function
```

### Step 4: Add Validation Schema

Add to `modules/validation.py`:

```python
# Define schema
my_source_schema = DataFrameSchema({
    "date": Column(pd.Timestamp, nullable=False, coerce=True),
    "metric_name": Column(str, nullable=False),
    "value": Column(float, nullable=True),
}, strict=False)

# Create validator class
class MySourceValidator(DataValidator):
    """Validator for My Source data."""
    def __init__(self):
        super().__init__(my_source_schema)

# Add to get_validator() function
def get_validator(data_type: str) -> DataValidator:
    validators = {
        # ... existing validators ...
        'my_source': MySourceValidator,
    }
    # ...

# Add to _get_primary_key_columns()
def _get_primary_key_columns(data_type: str) -> list:
    pk_mappings = {
        # ... existing mappings ...
        'my_source': ['date', 'metric_name'],
    }
    # ...
```

### Step 5: Register in Scheduler

#### Option A: GitHub Actions (Recommended for scheduled jobs)

Create `.github/workflows/my-source-refresh.yml`:

```yaml
name: My Source Data Refresh

on:
  schedule:
    - cron: '0 6 * * *'  # Daily at 6 AM UTC
  workflow_dispatch:  # Allow manual trigger

jobs:
  refresh:
    runs-on: ubuntu-latest
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
          
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          
      - name: Refresh My Source Data
        env:
          MY_SOURCE_API_KEY: ${{ secrets.MY_SOURCE_API_KEY }}
          DATABASE_BACKEND: postgresql
          DATABASE_URL: ${{ secrets.DATABASE_URL }}
        run: |
          python -c "from etl.sources.my_source import refresh_my_source_data; refresh_my_source_data()"
```

#### Option B: APScheduler Worker (`services/scheduler.py`)

```python
from etl.sources.my_source import refresh_my_source_data

class DataRefreshScheduler:
    def __init__(self):
        # ... existing code ...
        
    def schedule_jobs(self):
        # ... existing jobs ...
        
        # My Source refresh
        self.scheduler.add_job(
            refresh_my_source_data,
            trigger='cron',
            hour=6,
            minute=0,
            id='my_source_refresh',
            name='My Source Data Refresh'
        )
```

### Step 6 (Optional): Add API Read Endpoint

Add to `api/v1/routes/data.py`:

```python
@router.get("/my-source", response_model=List[Dict])
async def get_my_source_data(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    metric_name: Optional[str] = None,
):
    """
    Get My Source data.
    
    Args:
        start_date: Optional start date (YYYY-MM-DD)
        end_date: Optional end date (YYYY-MM-DD)
        metric_name: Optional metric name filter
    """
    db = get_db_connection()
    
    query = "SELECT * FROM my_source_data WHERE 1=1"
    params = []
    
    if start_date:
        query += " AND date >= ?"
        params.append(start_date)
    if end_date:
        query += " AND date <= ?"
        params.append(end_date)
    if metric_name:
        query += " AND metric_name = ?"
        params.append(metric_name)
    
    query += " ORDER BY date DESC"
    
    df = db.query(query, tuple(params) if params else None)
    
    return df.to_dict('records')
```

## Examples

### Example 1: Simple REST API

Source that fetches JSON from a public API:

```python
# etl/sources/crypto_prices.py
import pandas as pd
from modules.http_client import BaseAPIClient

def fetch_crypto_prices(symbols: list = ['BTC', 'ETH']) -> pd.DataFrame:
    client = BaseAPIClient('https://api.coinbase.com')
    
    data = []
    for symbol in symbols:
        response = client.get_json(f'/v2/prices/{symbol}-USD/spot')
        data.append({
            'symbol': symbol,
            'date': pd.Timestamp.now(),
            'price': float(response['data']['amount'])
        })
    
    return pd.DataFrame(data)
```

### Example 2: CSV File Download

Source that downloads and parses CSV:

```python
# etl/sources/treasury_yields.py
import pandas as pd
import requests

def fetch_treasury_yields() -> pd.DataFrame:
    url = 'https://home.treasury.gov/resource-center/data-chart-center/interest-rates/daily-treasury-rates.csv'
    
    df = pd.read_csv(url)
    df = df.rename(columns={'Date': 'date'})
    df['date'] = pd.to_datetime(df['date'])
    
    return df
```

## Best Practices

### 1. Error Handling

Always wrap API calls in try-except blocks:

```python
try:
    data = client.get_json('/endpoint')
except requests.HTTPError as e:
    if e.response.status_code == 429:
        logger.warning("Rate limit hit, retrying...")
        time.sleep(60)
        data = client.get_json('/endpoint')
    else:
        raise
```

### 2. Logging

Use structured logging for observability:

```python
logger.info(f"Fetching {source_name} data", extra={
    'source': source_name,
    'start_date': start_date,
    'end_date': end_date
})
```

### 3. Data Validation

Always validate data before inserting:

```python
validated_df = validate_and_clean(df, 'my_source', raise_errors=True)
```

### 4. Incremental Updates

Only fetch new data to save API calls:

```python
from modules.database.queries import get_latest_date

last_date = get_latest_date('my_source_data', 'date')
df = fetch_data(start_date=last_date)
```

### 5. Idempotency

Make refresh functions idempotent (safe to run multiple times):

```python
# Use UPSERT logic via primary keys
# PostgreSQL/DuckDB will automatically handle duplicates
# based on PRIMARY KEY constraints
```

### 6. Rate Limiting

Respect API rate limits:

```python
client = BaseAPIClient(
    base_url='https://api.example.com',
    rate_limit=(100, 60)  # 100 calls per 60 seconds
)
```

## Troubleshooting

### Issue: Schema validation fails

**Solution:** Check that DataFrame columns match the validation schema. Use `df.columns` to inspect.

### Issue: Data not appearing in database

**Solution:** Check logs for errors. Verify table exists with `db.table_exists('table_name')`.

### Issue: Rate limit errors

**Solution:** Reduce `rate_limit` in configuration or add delays between requests.

### Issue: Duplicate key errors

**Solution:** Ensure PRIMARY KEY columns are correctly defined in schema and DataFrame.

## Testing

Create a test for your new data source:

```python
# tests/test_my_source.py
import pytest
from etl.sources.my_source import fetch_data

def test_fetch_my_source():
    df = fetch_data(param1='test')
    
    assert not df.empty
    assert 'date' in df.columns
    assert 'value' in df.columns
    assert df['date'].dtype == 'datetime64[ns]'
```

## Summary

Adding a new data source is straightforward:

1. ✅ Configure in `modules/data_sources.py`
2. ✅ Create fetch logic in `etl/sources/`
3. ✅ Add database table schema
4. ✅ Add validation schema
5. ✅ Schedule via GitHub Actions or APScheduler
6. ✅ (Optional) Expose via API

For questions or issues, see the project README or create an issue on GitHub.
