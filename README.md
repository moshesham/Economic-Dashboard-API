# Economic Dashboard API

Production-ready, Docker-orchestrated economic data platform with FastAPI, PostgreSQL, Redis caching, and Streamlit dashboards.

## Overview
- FastAPI REST API for data, features, predictions, signals
- PostgreSQL (prod) and DuckDB (dev) via a unified database factory
- Redis for caching and lightweight queuing
- Worker for scheduled refresh jobs (APScheduler)
- Streamlit dashboard for visualization

## Architecture

```
FastAPI (:8000)  ─┬─ Redis (:6379)
Worker            ├─ PostgreSQL (:5432)
Streamlit (:8501) └─ DuckDB (dev)
```

## Quick Start

```powershell
# Start core services (Postgres, Redis)
docker-compose up -d postgres redis

# Initialize database (creates tables)
$env:DATABASE_BACKEND = "postgresql"; `
$env:DATABASE_URL = "postgresql://dashboard_user:dashboard_pass@localhost:5432/economic_dashboard"; `
python scripts/init_database.py

# Run API locally (dev)
$env:DATABASE_BACKEND = "postgresql"; `
$env:DATABASE_URL = "postgresql://dashboard_user:dashboard_pass@localhost:5432/economic_dashboard"; `
python -m api.main

# Open API docs
Invoke-WebRequest -Uri "http://localhost:8000/docs" -Method GET

# Optional: start full stack
docker-compose up -d
```

## Key Endpoints
- `/v1/data/fred/{series_id}`: FRED time series (e.g., `GDP`)
- `/v1/features/{ticker}`: Pre-computed technical features
- `/v1/predictions/{ticker}`: ML predictions and model metrics
- `/v1/signals`: Strategy signals
- `/v1/portfolio/optimize`: Portfolio optimization

## Configuration
- Set `DATABASE_BACKEND` to `postgresql` or `duckdb`
- Set `DATABASE_URL` for PostgreSQL (see `docker-compose.yml` defaults)
- Optional API keys via environment (FRED, NEWS, etc.)
- See `core/config.py` for all settings

## Development Notes
- Database factory: `modules/database/factory.py`
- PostgreSQL schema: `modules/database/postgres_schema.py`
- Validation: `modules/validation.py` (Pandera)
- HTTP clients: `modules/http_client.py`
- Ingestion routes: `api/v1/routes/ingest.py`

## Documentation
Start here: `docs/INDEX.md`
- Architecture & implementation: `docs/ARCHITECTURE_IMPLEMENTATION.md`
- Validation summary: `docs/VALIDATION_SUMMARY.md`
- Operations: `docs/DATA_REFRESH_SLA.md`, `docs/AUTOMATED_DATA_REFRESH.md`
- Features: `docs/NEWS_SENTIMENT_FEATURE.md`, `docs/FEATURE_API_KEY_MANAGEMENT.md`
- Guides: `docs/ADDING_DATA_SOURCES.md`, `docs/IP_ROTATION.md`

## License
Proprietary. Do not distribute without permission.
