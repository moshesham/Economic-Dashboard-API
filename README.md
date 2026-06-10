# 📊 Economic Dashboard API

**Production-grade economic analysis platform with a multi-backend architecture (PostgreSQL & DuckDB), FastAPI REST services, and an extensible ETL framework.**

[![Python 3.12](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.136+-green.svg)](https://fastapi.tiangolo.com)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15+-blue.svg)](https://www.postgresql.org/)
[![Docker](https://img.shields.io/badge/Docker-Ready-blue.svg)](https://www.docker.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## 🚀 What's New: Modernized IMF SDMX Integration (June 2026)

We have refactored the International Monetary Fund (IMF) data ingestion engine to comply with official **SDMX 3.0 guidelines**. 

* **Modern Client**: Migrated from the deprecated JSON API to the robust `sdmx1` library querying the modern `api.imf.org` endpoint.
* **Streamlined Exchange Rates**: Fetches End-of-Period exchange rates using the official `'ER'` dataflow layout (`COUNTRY.INDICATOR.TRANSFORMATION.FREQUENCY`).
* **World Economic Outlook (WEO)**: Queries core macroeconomic projections (GDP growth, inflation, unemployment, government expenditure) from the `'WEO'` dataflow (`COUNTRY.INDICATOR.FREQUENCY`).
* **Automatic standardizations**: Auto-converts ISO-2 country codes to ISO-3 codes for native queries, mapping outputs back to the database schema.

---

## 🏛️ Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                  Orchestration Layer                        │
│  GitHub Actions │ APScheduler │ Manual API Triggers         │
└───────────────────────┬─────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────┐
│                  ETL / Data Sources                         │
│  modules/*_data.py (FRED, Yahoo, IMF SDMX, OECD, BLS)       │
│  Uses: http_client.py + validation.py (Pandera Schemas)     │
└───────────────────────┬─────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────┐
│                  Database Layer (Factory)                   │
│  factory.py → DuckDBBackend (Dev) OR PostgreSQLBackend (Prod)│
│  queries.py → Unified insert and select operations          │
└───────────────────────┬─────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────┐
│                  Consumption Layer                          │
│  FastAPI (api/main.py) │ Streamlit (pages/*.py)            │
└─────────────────────────────────────────────────────────────┘
```

### 🐳 Dockerized Services:
* 🐘 **PostgreSQL** – Persistent production-ready database.
* ⚡ **Redis** – API caching and background job management.
* 🚀 **FastAPI** – REST endpoints (`http://localhost:8000`).
* ⚙️ **Worker** – Scheduled ETL automation (APScheduler).
* 📊 **Dashboard** – Interactive Streamlit interface (`http://localhost:8501`).

---

## 🛠️ Quick Start

### Option 1: Local Development (No Docker)
1. **Clone the repository**:
   ```bash
   git clone https://github.com/moshesham/Economic-Dashboard-API.git
   cd Economic-Dashboard-API
   ```
2. **Create and activate the virtual environment**:
   ```bash
   python -m venv .venv
   .venv\Scripts\activate
   ```
3. **Install dependencies**:
   ```bash
   python -m pip install --upgrade pip
   python -m pip install -r requirements.txt
   ```
4. **Set up environment configuration**:
   ```bash
   copy .env.example .env
   # Edit .env to set your API keys and configuration
   ```
5. **Run the API & Dashboard**:
   ```bash
   # Terminal 1: FastAPI API
   python -m uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload

   # Terminal 2: Streamlit Dashboard
   python -m streamlit run app.py --server.port=8501 --server.address=0.0.0.0
   ```

### Option 2: Production-Ready (Docker Compose)
1. **Configure environment backend**:
   Ensure `.env` has:
   ```env
   DATABASE_BACKEND=postgresql
   DATABASE_URL=postgresql://dashboard_user:dashboard_pass@postgres:5432/economic_dashboard
   ```
2. **Launch services**:
   ```bash
   docker-compose up -d
   ```
3. **Verify backend status**:
   ```bash
   curl http://localhost:8000/health
   ```

---

## 📊 Supported Data Sources

| Source | Description | Indicators Covered |
|---|---|---|
| **IMF SDMX (New)** | International Monetary Fund SDMX 3.0 API | Exchange rates (ER), GDP, Inflation, Unemployment (WEO) |
| **FRED** | Federal Reserve Economic Data | Interest rates, GDP growth, US CPI, Treasury yields |
| **Yahoo Finance** | Global Equity Markets | Stock price historical OHLCV, index data, ETF flows |
| **OECD** | Organization for Economic Co-operation | Composite Leading Indicators (CLI), country productivity metrics |
| **BLS** | Bureau of Labor Statistics | Detailed employment reports, CPI baskets, labor wages |
| **Census Bureau** | US Census Bureau | Retail sales, housing starts, international trade flows |
| **EIA** | Energy Information Administration | Crude oil prices, inventories, gas, electricity stats |
| **SEC EDGAR** | US SEC Filings | Forms 10-K/10-Q, insider transactions, fails-to-deliver |

---

## 📈 Advanced Analytics & Features

* **Technical Indicators**: Real-time calculators for RSI, MACD, Bollinger Bands, Stochastic, and Trend Strength indicators.
* **Machine Learning**: Future price direction predictions utilizing tree-based classifiers (XGBoost, LightGBM).
* **Macro Risk Signals**: Risk scores assessing margin call risks, recession probabilities, and anomalous insider trading activity.
* **Portfolio Allocator**: Automated Black-Litterman optimization and macro-driven sector rotation engine.

---

## 🔗 Key API Endpoints

### 🔍 Data Retrieval
* `GET /v1/data/imf/exchange-rates` – Retrieve exchange rate metrics.
* `GET /v1/data/worldbank` – Query international development statistics.
* `GET /v1/data/fred` – Retrieve FRED economic time series.
* `GET /v1/data/stock` – Fetch global equity OHLCV data.
* `GET /v1/features/technical` – Fetch technical analysis indicators.
* `GET /v1/signals/margin-risk` – Retrieve computed risk warnings.

### 📥 Data Ingestion (Authentication Required)
* `POST /v1/ingest/fred` – Upload structured JSON for FRED series.
* `POST /v1/ingest/stock` – Ingest asset pricing tables.
* `POST /v1/ingest/csv/{data_type}` – Ingest CSV table imports.

---

## 🧪 Testing and Quality Assurance

A comprehensive suite of unit and integration tests is included.

```bash
# Run the entire test suite
pytest -v

# Run IMF SDMX integration tests only
pytest -v tests/test_imf_data.py

# Run validators and open data client checks
pytest -v tests/test_open_data_sources.py
```

---

## ⚙️ Configuration & Environment

Modify the `.env` configuration file to configure databases and API tokens:

```env
# Database Settings
DATABASE_BACKEND=postgresql # or duckdb
DATABASE_URL=postgresql://user:password@host:5432/db

# API Authentication Tokens
FRED_API_KEY=your_key
NEWS_API_KEY=your_key
BLS_API_KEY=your_key       # Optional: increases rate limits
CENSUS_API_KEY=your_key    # Required for Census Bureau features
EIA_API_KEY=your_key       # Required for Energy statistics

# Cache Settings
REDIS_URL=redis://redis:6379/0
```

---

## 📝 License

Distributed under the **MIT License**. See [LICENSE](LICENSE) for more information.
