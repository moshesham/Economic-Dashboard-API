# Economic Dashboard API

Docker-driven, API-first economic analysis platform with enhanced analytics.

## Architecture

\\\
+-----------------------------------------------------------------------------+
|                         Economic Dashboard Platform                          |
+-----------------------------------------------------------------------------+
|                                                                              |
|  +------------+    +------------+    +------------+                          |
|  |   FastAPI  |    |   Worker   |    |  Dashboard |                          |
|  |   (API)    |    |(APScheduler)|   | (Streamlit)|                          |
|  |   :8000    |    |            |    |   :8501    |                          |
|  +-----+------+    +-----+------+    +-----+------+                          |
|        |                 |                 |                                 |
|        +-----------------+-----------------+                                 |
|                          |                                                   |
|                 +--------+--------+                                          |
|                 |     Redis       |                                          |
|                 |   (Cache/Queue) |                                          |
|                 |     :6379       |                                          |
|                 +--------+--------+                                          |
|                          |                                                   |
|                 +--------+--------+                                          |
|                 |     DuckDB      |                                          |
|                 |   (Database)    |                                          |
|                 |  Shared Volume  |                                          |
|                 +-----------------+                                          |
|                                                                              |
+-----------------------------------------------------------------------------+
\\\

## Quick Start

\\\ash
# Start all services
docker-compose up -d

# View API docs
open http://localhost:8000/docs

# View Dashboard
open http://localhost:8501
\\\

## API Endpoints

- /v1/data/{source} - Raw data access
- /v1/features/{ticker} - Pre-computed features
- /v1/predictions/{ticker} - ML predictions with SHAP
- /v1/signals/ - Trading signals
- /v1/portfolio/optimize - Portfolio optimization

See full documentation in the /docs folder.
