# Economic Dashboard API

**Production-ready economic analysis platform with PostgreSQL backend, FastAPI, and extensible ETL framework.**

[![Python 3.11](https://img.shields.io/badge/python-3.11-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.109+-green.svg)](https://fastapi.tiangolo.com)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15-blue.svg)](https://www.postgresql.org/)
[![Docker](https://img.shields.io/badge/Docker-Ready-blue.svg)](https://www.docker.com/)
[![CI](https://github.com/moshesham/Economic-Dashboard-API/workflows/CI%20-%20Test%20%26%20Lint/badge.svg)](https://github.com/moshesham/Economic-Dashboard-API/actions)
[![Security](https://github.com/moshesham/Economic-Dashboard-API/workflows/Security%20Scan/badge.svg)](https://github.com/moshesham/Economic-Dashboard-API/actions)

## 🎉 What's New - December 2025

**Major Architecture Refactor Complete:**
- ✅ **PostgreSQL Support** - Production-ready database with connection pooling
- ✅ **Multi-Backend** - Switch between DuckDB (dev) and PostgreSQL (prod) via environment variable
- ✅ **API Ingestion** - POST data via REST API with full validation
- ✅ **Extensibility Framework** - Add new data sources in 5 simple steps
- ✅ **Unified HTTP Client** - Built-in rate limiting, retries, and error handling
- ✅ **Data Validation** - Pandera schemas ensure data quality

**Production-Grade Features (NEW):**
- ✅ **API Response Caching** - Redis-based caching with automatic cache invalidation
- ✅ **Centralized Logging** - Structured JSON logging with correlation IDs
- ✅ **Request Tracking** - Full request tracing across distributed systems
- ✅ **80% Test Coverage** - Comprehensive unit and integration tests
- ✅ **Security Scanning** - Automated vulnerability scanning with CodeQL and Bandit

📖 **[Read the Full Refactor Summary](docs/REFACTOR_SUMMARY.md)**  
📖 **[Production Features Documentation](docs/PRODUCTION_FEATURES.md)**

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                  Orchestration Layer                        │
│  GitHub Actions │ APScheduler │ Manual API Calls           │
└───────────────────────┬─────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────┐
│                  ETL / Data Sources                         │
│  etl/sources/*.py (FRED, Yahoo, CBOE, ICI, etc.)           │
│  Uses: http_client.py + validation.py                      │
└───────────────────────┬─────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────┐
│                  Database Layer (Factory)                   │
│  factory.py → DuckDBBackend OR PostgreSQLBackend           │
│  queries.py → Reusable query functions                     │
└───────────────────────┬─────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────┐
│                  Consumption Layer                          │
│  FastAPI (api/main.py) │ Streamlit (pages/*.py)            │
└─────────────────────────────────────────────────────────────┘
```

**Docker Services:**
- 🐘 **PostgreSQL** - Production database with persistent storage
- 🚀 **FastAPI** - REST API for data access and ingestion (`:8000`)
- ⚡ **Worker** - Background ETL jobs (APScheduler)
- 📊 **Dashboard** - Streamlit interactive UI (`:8501`)
- 🔴 **Redis** - Caching and job queue (`:6379`)

---

## Quick Start

### Option 1: Development (DuckDB - Local File Database)
```bash
# Clone repository
git clone https://github.com/moshesham/Economic-Dashboard-API.git
cd Economic-Dashboard-API

# Create environment file
cp .env.example .env
# Edit .env: Set DATABASE_BACKEND=duckdb

# Add your API keys
# FRED_API_KEY=your_key_here
# NEWS_API_KEY=your_key_here

# Start services
docker-compose up -d

# View API documentation
open http://localhost:8000/docs

# View Dashboard
open http://localhost:8501
```

### Option 2: Production (PostgreSQL - Scalable Database)
```bash
# Configure .env for PostgreSQL
DATABASE_BACKEND=postgresql
DATABASE_URL=postgresql://dashboard_user:dashboard_pass@postgres:5432/economic_dashboard

# Start PostgreSQL first
docker-compose up -d postgres

# Wait for PostgreSQL to initialize (check logs)
docker-compose logs -f postgres

# Start all services
docker-compose up -d

# Verify deployment
curl http://localhost:8000/health
```

📖 **[Full Deployment Guide](docs/DEPLOYMENT_CHECKLIST.md)**

---

## Features

### 📊 Data Sources

**Core Data Sources:**
- **FRED** - Federal Reserve Economic Data (GDP, CPI, unemployment, interest rates)
- **Yahoo Finance** - Stock OHLCV data for indices, ETFs, and individual stocks
- **CBOE** - VIX volatility index and term structure
- **ICI** - Investment Company Institute ETF flow statistics
- **News API** - News articles for sentiment analysis
- **SEC EDGAR** - Company filings, insider trading, fails-to-deliver

**Open Data Sources (New):**
- **World Bank** - 1,400+ economic indicators for 217 countries (GDP, inflation, trade, development)
- **IMF** - Exchange rates, international financial statistics, World Economic Outlook
- **OECD** - Leading indicators, productivity data for 38 member countries
- **BLS** - US Bureau of Labor Statistics (employment, CPI, wages, granular labor data)
- **Census Bureau** - Retail sales, housing starts, international trade statistics
- **EIA** - Energy Information Administration (oil, gas, electricity prices and inventories)

### 📈 Analytics & Features
- **Technical Indicators** - RSI, MACD, Bollinger Bands, ADX, ATR, Stochastic, MFI
- **ML Predictions** - Multi-horizon stock predictions using XGBoost and LightGBM
- **Risk Signals** - Margin call risk monitor, recession probability, insider activity tracker
- **Portfolio Tools** - Black-Litterman allocation, sector rotation signals

---

## API Endpoints

### Health & Documentation
- `GET /health` - API health status
- `GET /docs` - Interactive API documentation (Swagger UI)
- `GET /redoc` - Alternative API documentation (ReDoc)

### Data Retrieval
- `GET /v1/data/fred` - Retrieve FRED economic series
- `GET /v1/data/stock` - Get stock OHLCV data
- `GET /v1/data/options` - Options metrics
- `GET /v1/features/technical` - Technical indicators
- `GET /v1/predictions/latest` - Latest ML predictions
- `GET /v1/signals/margin-risk` - Margin call risk assessment

**Open Data Sources (New):**
- `GET /v1/data/worldbank` - World Bank economic indicators
- `GET /v1/data/imf/exchange-rates` - IMF exchange rates
- `GET /v1/data/oecd` - OECD leading indicators and productivity
- `GET /v1/data/bls` - BLS employment, CPI, wages
- `GET /v1/data/census` - Census retail sales, housing, trade
- `GET /v1/data/eia` - EIA energy prices and inventories

### Data Ingestion (Authentication Required)
- `POST /v1/ingest/fred` - Ingest FRED data (JSON)
- `POST /v1/ingest/stock` - Ingest stock data (JSON)
- `POST /v1/ingest/csv/{data_type}` - Upload CSV file
- `POST /v1/ingest/bulk/{data_type}` - Background bulk ingestion
- `GET /v1/ingest/status/{job_id}` - Check ingestion job status

**Example:**
```bash
curl -X POST http://localhost:8000/v1/ingest/fred \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '[{
    "series_id": "GDP",
    "date": "2024-01-01",
    "value": 21000.5
  }]'
```

---

## Development

### Project Structure
```
Economic-Dashboard-API/
├── api/                    # FastAPI application
│   ├── main.py            # Application entry point
│   └── v1/routes/         # API endpoints
│       ├── data.py        # Data retrieval
│       ├── ingest.py      # Data ingestion
│       ├── features.py    # Feature engineering
│       └── predictions.py # ML predictions
├── etl/                   # ETL pipeline
│   ├── sources/           # Data source fetch modules
│   ├── loaders/           # Data loading utilities
│   └── jobs/              # Scheduled job definitions
├── modules/               # Core business logic
│   ├── database/          # Database abstraction layer
│   │   ├── factory.py     # Multi-backend factory
│   │   ├── queries.py     # Pre-built queries
│   │   ├── schema.py      # DuckDB schema
│   │   └── postgres_schema.py  # PostgreSQL schema
│   ├── http_client.py     # HTTP client base class
│   ├── validation.py      # Data validation schemas
│   └── data_sources.py    # Data source registry
├── pages/                 # Streamlit dashboard pages
├── services/              # Background services
│   └── scheduler.py       # APScheduler job scheduler
├── docs/                  # Documentation
│   ├── ADDING_DATA_SOURCES.md  # How to add new sources
│   ├── REFACTOR_SUMMARY.md     # Architecture overview
│   ├── DEPLOYMENT_CHECKLIST.md # Production deployment
│   └── QUICK_REFERENCE.md      # Quick reference guide
├── docker-compose.yml     # Docker services
├── Dockerfile            # API container
└── requirements.txt      # Python dependencies
```

### Adding a New Data Source

It's now incredibly easy to add new data sources! Follow the 5-step checklist:

1. **Define source config** in `modules/data_sources.py`
2. **Create fetch module** in `etl/sources/{source_name}.py`
3. **Add database schema** (PostgreSQL or DuckDB)
4. **Add validation schema** in `modules/validation.py`
5. **Register scheduler** (GitHub Actions or APScheduler)

📖 **[Complete Guide: Adding Data Sources](docs/ADDING_DATA_SOURCES.md)**

---

## Configuration

### Environment Variables

```env
# Database Backend (duckdb or postgresql)
DATABASE_BACKEND=postgresql

# PostgreSQL (when DATABASE_BACKEND=postgresql)
DATABASE_URL=postgresql://user:pass@host:5432/database
# Or individual components:
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=economic_dashboard
POSTGRES_USER=dashboard_user
POSTGRES_PASSWORD=your_secure_password

# DuckDB (when DATABASE_BACKEND=duckdb)
DUCKDB_PATH=./data/duckdb/economic_dashboard.duckdb

# API Keys
FRED_API_KEY=your_fred_api_key
NEWS_API_KEY=your_news_api_key
ALPHA_VANTAGE_API_KEY=your_av_key

# Open Data Sources API Keys (Optional/Required)
BLS_API_KEY=your_bls_key  # Optional: 500/day with key, 25/day without
CENSUS_API_KEY=your_census_key  # Required for Census Bureau data
EIA_API_KEY=your_eia_key  # Required for EIA energy data

# API Settings
API_KEY_ENABLED=true
API_SECRET_KEY=your_secret_key
API_RATE_LIMIT=100  # requests per minute

# Redis
REDIS_URL=redis://redis:6379/0
```

---

## Documentation

- 📖 [Quick Reference Guide](docs/QUICK_REFERENCE.md) - Common tasks and examples
- 📖 [Adding Data Sources](docs/ADDING_DATA_SOURCES.md) - Step-by-step guide
- 📖 [Architecture Refactor Summary](docs/REFACTOR_SUMMARY.md) - What changed and why
- 📖 [Deployment Checklist](docs/DEPLOYMENT_CHECKLIST.md) - Production deployment
- 📖 [API Documentation](http://localhost:8000/docs) - Interactive API docs (when running)

---

## Testing

```bash
# Run all tests
pytest tests/

# Test specific module
pytest tests/test_database.py

# Test with coverage
pytest --cov=modules tests/
```

---

## Monitoring & Maintenance

### Health Checks
```bash
# API health
curl http://localhost:8000/health

# Database connection
curl http://localhost:8000/v1/data/health

# Check logs
docker-compose logs -f api
docker-compose logs -f worker
docker-compose logs -f postgres
```

### Database Maintenance
```bash
# Access PostgreSQL
docker-compose exec postgres psql -U dashboard_user economic_dashboard

# Backup database
docker-compose exec postgres pg_dump -U dashboard_user economic_dashboard > backup.sql

# Restore database
cat backup.sql | docker-compose exec -T postgres psql -U dashboard_user economic_dashboard
```

---

## Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## Acknowledgments

- Federal Reserve Economic Data (FRED) for economic indicators
- Yahoo Finance for market data
- CBOE for volatility metrics
- FastAPI for the excellent web framework
- Streamlit for interactive dashboards

---

## Support

- 📧 Email: moshesham@example.com
- 🐛 Issues: [GitHub Issues](https://github.com/moshesham/Economic-Dashboard-API/issues)
- 💬 Discussions: [GitHub Discussions](https://github.com/moshesham/Economic-Dashboard-API/discussions)

---

**Built with ❤️ for the data science and finance community**
