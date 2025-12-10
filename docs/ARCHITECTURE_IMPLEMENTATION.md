# Architecture & Implementation

A consolidated guide combining the refactor overview and implementation details.

## High-Level Architecture
- FastAPI API (`api/`)
- Database factory (DuckDB dev, PostgreSQL prod)
- Validation via Pandera
- HTTP client strategy with rate limiting & retries
- Background worker for scheduled ingestions
- Streamlit dashboard for visualization

## Core Modules
- `modules/database/factory.py`: Backend selection, connection pooling, shared interface
- `modules/database/postgres_schema.py`: PostgreSQL tables and indexes
- `modules/validation.py`: Schemas and `validate_and_clean`
- `modules/http_client.py`: BaseAPIClient + FRED/Yahoo/CBOE/ICI/News clients
- `api/v1/routes/ingest.py`: JSON/CSV ingestion endpoints with API key auth

## Data Flow
1. Fetch via client (rate-limited)
2. Validate with Pandera
3. Insert via DB factory (bulk insert, `to_sql` for Postgres)
4. Log refresh & expose via API endpoints

## Extensibility
- Add sources via `docs/ADDING_DATA_SOURCES.md` (5-step process)
- Register configs in a central registry (source id, schedule, schema, table)

## Operations
- Use `docker-compose` for services
- Initialize DB: `scripts/init_database.py`
- Health checks: `/health` endpoint (database, redis)
