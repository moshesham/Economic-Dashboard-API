# PostgreSQL Initialization Scripts

This directory contains SQL scripts that are automatically executed when the PostgreSQL container starts for the first time.

## Execution Order

Scripts are executed in alphabetical order by the PostgreSQL Docker image:

1. `01_schema.sql` - Creates all tables, indexes, and triggers

## Adding New Scripts

To add additional initialization:

1. Create a new `.sql` file with a numeric prefix (e.g., `02_seed_data.sql`)
2. Place it in this directory
3. Restart the PostgreSQL container (or delete the volume to reinitialize)

## Schema Overview

### Core Data Tables
- `fred_data` - Federal Reserve Economic Data
- `yfinance_ohlcv` - Stock market OHLCV data
- `cboe_vix_history` - VIX historical data
- `ici_etf_weekly_flows` - ETF flow data (weekly)
- `ici_etf_monthly_flows` - ETF flow data (monthly)
- `news_sentiment` - News articles with sentiment scores

### Feature Tables
- `technical_features` - Technical indicators (RSI, MACD, etc.)
- `options_data` - Options market data

### ML Tables
- `ml_predictions` - Model predictions
- `model_performance` - Model metrics over time

### System Tables
- `data_refresh_log` - Audit trail for data refreshes

## Features

- **Automatic Timestamps**: `created_at` and `updated_at` columns with triggers
- **Conflict Handling**: Unique constraints on key combinations
- **Optimized Indexes**: Indexes on commonly queried columns
- **Comments**: Table comments for documentation

## Manual Execution

To run these scripts manually:

```bash
docker-compose exec postgres psql -U dashboard_user -d economic_dashboard -f /docker-entrypoint-initdb.d/01_schema.sql
```
