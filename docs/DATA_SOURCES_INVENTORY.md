# 📊 Complete Data Sources Inventory

**Economic Dashboard API - All Data Sources Reference Document**

---

## Overview

The Economic Dashboard API integrates **15+ major data sources** spanning global economic indicators, financial markets, labor statistics, and energy data. This document provides a comprehensive inventory of all data sources, their configurations, API endpoints, and integration details.

**Last Updated**: 2026-06-11  
**Total Data Sources**: 15+  
**Database Backend**: PostgreSQL (production) / DuckDB (development)

---

## 🗂️ Data Sources by Category

### 1️⃣ FINANCIAL MARKETS & EQUITY DATA

#### **1.1 Yahoo Finance (yfinance)**
- **Type**: REST API
- **Module**: `modules/data_loader.py`
- **Database Table**: `yfinance_ohlcv`
- **Data Coverage**: Global stock OHLCV (Open, High, Low, Close, Volume)
- **Frequency**: Daily
- **SLA**: Max staleness 1 day
- **API Endpoint**: `GET /v1/data/stocks/{ticker}`
- **Supported Tickers**: S&P 500, international indices, ETFs
- **Rate Limiting**: Batch size ~100 stocks/request
- **Authentication**: None (public API)
- **Cache**: 24 hours
- **Features**:
  - Historical price data
  - Dividend information
  - Stock splits
  - Volume metrics
- **Typical Use Cases**:
  - Portfolio analysis
  - Technical indicator calculation
  - Price-based risk assessments

#### **1.2 CBOE VIX (Volatility Index)**
- **Type**: CSV Download
- **Module**: `modules/cboe_vix_data.py`
- **Database Table**: 
  - `cboe_vix_history` (historical volatility)
  - `cboe_vix_term_structure` (futures term structure)
- **Data Coverage**: VIX index, VIX futures, volatility curves
- **Frequency**: Daily (updated after market close)
- **SLA**: Max staleness 6 hours
- **API Endpoint**: Not directly exposed; used internally
- **Indicators Tracked**:
  - VIX (30-day implied volatility)
  - VIX9D (9-day variant)
  - VIX3M (3-month variant)
  - VIX1Y (1-year variant)
  - Term structure (front/back spreads)
- **Authentication**: None
- **Features**:
  - Regime detection (contango/backwardation)
  - Volatility clustering analysis
  - Risk premium calculations

#### **1.3 SEC EDGAR (Securities and Exchange Commission)**
- **Type**: REST API
- **Module**: `modules/sec_data_loader.py` (OOP refactored)
- **Database Tables**:
  - `sec_submissions` (Form metadata)
  - `sec_financial_statements` (XBRL parsed facts)
  - `sec_company_facts` (Normalized CIK-tagged facts)
  - `sec_filings` (Filing summaries)
  - `sec_13f_holdings` (Institutional holdings)
  - `sec_fails_to_deliver` (Fails-to-deliver data)
- **Data Coverage**: 10-K, 10-Q, 8-K, 4, SD, 13F filings
- **Frequency**: Real-time (as filed)
- **SLA**: Max staleness 1 hour
- **API Endpoints**:
  - `GET /v1/data/sec/filings/{ticker}` - Filings by ticker
  - `GET /v1/data/sec/filings/{ticker}?form_type=10-K` - Filtered by form
  - `GET /v1/data/sec/insider/{ticker}` - Insider transactions
- **Company Tickers URL**: `https://www.sec.gov/files/company_tickers.json`
- **Base API URLs**:
  - Facts: `https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json`
  - Submissions: `https://data.sec.gov/submissions/CIK{cik}.json`
- **Authentication**: None (public API)
- **Rate Limiting**: ~10 req/sec recommended
- **Features**:
  - CIK lookup by ticker
  - Financial statement extraction (assets, liabilities, equity)
  - Insider trading sentiment
  - Fails-to-deliver monitoring
  - 13F institutional positioning
- **Key Methods**:
  - `SECDataLoader.lookup_ticker(ticker)` → CIK
  - `get_sec_filings(ticker, form_type, limit)`
  - `get_recent_filings(ticker, days)`

---

### 2️⃣ MACROECONOMIC INDICATORS

#### **2.1 FRED (Federal Reserve Economic Data)**
- **Type**: REST API
- **Module**: `modules/data_loader.py` (legacy) / via database integration
- **Database Table**: `fred_data`
- **Data Coverage**: 400,000+ US economic time series
- **Frequency**: Daily/Weekly/Monthly (varies by series)
- **SLA**: Max staleness 24 hours
- **API Endpoint**: 
  - `GET /v1/data/fred/{series_id}` - Single series
  - `GET /v1/data/fred` - List all available series
- **Common Series IDs**:
  - **GDP**: `GDP`, `GDPC1` (real), `GDPCA` (annualized)
  - **Inflation**: `CPIAUCSL` (CPI), `PCEPI` (PCE)
  - **Unemployment**: `UNRATE` (rate), `PAYEMS` (employment)
  - **Interest Rates**: `DGS10` (10Y Treasury), `DGS2` (2Y Treasury), `FEDFUNDS` (Fed Funds)
  - **Housing**: `HOUST` (housing starts), `MORTGAGE30US` (30Y mortgage)
  - **Manufacturing**: `INDPRO` (industrial production), `MMNRNJ` (manufacturing hours)
- **Authentication**: Requires `FRED_API_KEY` (free registration at fred.stlouisfed.org)
- **Features**:
  - Automatic series metadata lookup
  - Date range filtering
  - Standardized time series format
- **Typical Use Cases**:
  - Macroeconomic trend analysis
  - Recession probability modeling
  - Inflation forecasting

#### **2.2 IMF SDMX (International Monetary Fund)**
- **Type**: REST API (SDMX 3.0 standard)
- **Module**: `modules/imf_data.py`
- **Database Tables**:
  - `imf_exchange_rates` (Currency exchange rates)
  - `imf_indicators` (World Economic Outlook projections)
- **Data Coverage**: 188 IMF member countries + advanced economies
- **Frequency**: Quarterly/Annual (varies by dataflow)
- **SLA**: Max staleness 1 month
- **API Endpoints**:
  - `GET /v1/data/imf/exchange-rates` - Exchange rates
  - Related: IMF indicator data stored in database
- **Base URL**: `https://api.imf.org/core/rest`
- **Dataflows Covered**:
  - **ER** (Exchange Rates): End-of-Period (EOP) vs USD
    - Query Pattern: `COUNTRY.INDICATOR.TRANSFORMATION.FREQUENCY`
    - Example: `US.EXJPUS.A` (US-JPY annual end-of-period)
  - **WEO** (World Economic Outlook): Macroeconomic projections
    - Query Pattern: `COUNTRY.INDICATOR.FREQUENCY`
    - Indicators: GDP growth, inflation, unemployment, gov't expenditure
- **Features**:
  - Auto ISO-2 → ISO-3 country code conversion
  - SDMX dimension handling
  - Automatic data standardization
- **Authentication**: None (public SDMX API)

#### **2.3 World Bank**
- **Type**: REST API
- **Module**: `modules/worldbank_data.py`
- **Database Table**: `worldbank_indicators`
- **Data Coverage**: 1,400+ development indicators for 217 countries
- **Frequency**: Annual/Biennial (varies by indicator)
- **SLA**: Max staleness 3 months
- **API Endpoint**: `GET /v1/data/worldbank`
- **Base URL**: `https://api.worldbank.org/v2`
- **Popular Indicators**:
  - **GDP**: `NY.GDP.MKTP.CD` (current USD), `NY.GDP.MKTP.KD` (constant LCU)
  - **Population**: `SP.POP.TOTL`
  - **Unemployment**: `SP.URB.TOTL.IN.ZS`
  - **Trade**: `NE.EXP.GNFS.CD` (exports), `NE.IMP.GNFS.CD` (imports)
  - **Inflation**: `FP.CPI.TOTL` (consumer price index)
- **Authentication**: None (public API)
- **Features**:
  - 217-country coverage
  - Standardized indicator codes
  - Decade-long historical records
- **Query Parameters**:
  - `country_code` (ISO3, e.g., "USA", "CHN")
  - `indicator` (WB indicator code)
  - `start_year`, `end_year`

#### **2.4 OECD (Organization for Economic Co-operation and Development)**
- **Type**: REST API (SDMX)
- **Module**: `modules/oecd_data.py`
- **Database Table**: `oecd_indicators`
- **Data Coverage**: 38 member countries + partnerships
- **Frequency**: Monthly/Quarterly/Annual (varies)
- **SLA**: Max staleness 1 month
- **API Endpoint**: `GET /v1/data/oecd`
- **Base URL**: `https://stats.oecd.org/`
- **Key Datasets**:
  - **CLI** (Composite Leading Indicators): Cyclical turning points, recession signals
  - **STLABOUR**: Labor market statistics
  - **ALFS**: Average labor force survey
  - **QNAA**: Quarterly national accounts
  - **ANA**: Annual national accounts
- **Features**:
  - Leading indicator (CLI) for early recession detection
  - Standardized labor metrics across OECD
  - GDP and productivity measurements
- **Query Parameters**:
  - `country_code` (OECD member code)
  - `indicator` (dataset ID)
  - `start_date`, `end_date`

#### **2.5 BLS (Bureau of Labor Statistics)**
- **Type**: REST API (JSON)
- **Module**: `modules/bls_data.py`
- **Database Table**: `bls_data`
- **Data Coverage**: US labor market, employment, wages, CPI granular data
- **Frequency**: Monthly
- **SLA**: Max staleness 2 weeks
- **API Endpoint**: `GET /v1/data/bls`
- **Base URL**: `https://api.bls.gov/publicAPI/v2`
- **Popular Series IDs**:
  - **Employment**:
    - `LNS14000000` (Unemployment Rate)
    - `PAYEMS` (Total Nonfarm Employment)
    - `CES0500000001` (Average hourly earnings, private)
  - **CPI Components**:
    - `CPIAUCSL` (CPI All Urban Consumers)
    - `CUUR0000SAD` (Apparel)
    - `CUUR0000SAF` (Food and beverages)
    - `CUUR0000SAH` (Shelter)
  - **Wages**:
    - `ECI02000` (Employment Cost Index)
    - `ENUUS` (Average weekly earnings)
- **Authentication**: Optional `BLS_API_KEY` (free registration increases rate limit)
- **Features**:
  - Granular occupation/industry breakdowns
  - Regional area disaggregation
  - CPI sub-component tracking
  - Wage growth monitoring

#### **2.6 Census Bureau (EITS: Economic Indicators Tracking System)**
- **Type**: REST API (Census EITS)
- **Module**: `modules/census_data.py`
- **Database Table**: `census_data`
- **Data Coverage**: Real-time and recent economic indicators
- **Frequency**: Weekly/Monthly (varies)
- **SLA**: Max staleness 1 week
- **API Endpoint**: `GET /v1/data/census`
- **Base URL**: `https://www.census.gov/data/timeseries/eits`
- **Key Datasets**:
  - **Retail Sales** (marts):
    - Series: Department store sales, used car sales index
    - Frequency: Weekly
  - **Construction** (resconst):
    - Housing starts, building permits
    - Frequency: Monthly
  - **Trade** (imp_exp, intl_trade):
    - Import/export values
    - Frequency: Monthly
  - **Manufacturing Production**:
    - Production indices, orders
- **Authentication**: Requires `CENSUS_API_KEY` (free)
- **Features**:
  - High-frequency leading indicators (weekly updates)
  - Real-time economic pulse
  - Trade flow monitoring
- **Dataset Mapping**:
  - `marts` → Retail sales
  - `resconst` → Residential construction
  - Supports dataset-specific parameter variations

#### **2.7 EIA (Energy Information Administration)**
- **Type**: REST API
- **Module**: `modules/eia_data.py`
- **Database Table**: `eia_data`
- **Data Coverage**: US energy markets (oil, gas, electricity, coal)
- **Frequency**: Daily/Weekly (real-time for prices)
- **SLA**: Max staleness 1 day
- **API Endpoint**: `GET /v1/data/eia`
- **Base URL**: `https://api.eia.gov/v1`
- **Series IDs** (commonly tracked):
  - **Crude Oil**:
    - `PET.RBRTE.D` (WTI daily)
    - `PET.DCRRIS.D` (Cushing stocks)
  - **Natural Gas**:
    - `NG.RNGSP.D` (Henry Hub spot price)
    - `NG.N3087US2.D` (Liquefied natural gas import price)
  - **Electricity**:
    - `ELEC.PRICE.CA-ALL.M` (California avg price)
  - **Gasoline**:
    - `PET.EMD_EPD2DXL0_PTE_NUS_DPG.W` (US all grades)
- **Authentication**: Requires `EIA_API_KEY` (free registration)
- **Features**:
  - Real-time commodity tracking
  - Strategic reserve monitoring
  - Energy inflation indicators

---

### 3️⃣ CRYPTOCURRENCY DATA

#### **3.1 CoinGecko API**
- **Type**: REST API
- **Module**: `modules/crypto_data.py`
- **Database Table**: None (on-demand fetching)
- **Data Coverage**: 10,000+ cryptocurrencies
- **Frequency**: Real-time (5-minute updates)
- **SLA**: Max staleness 5 minutes
- **API Endpoint**: Not directly exposed; internal use
- **Base URL**: `https://api.coingecko.com/api/v3`
- **Supported Assets**:
  - Bitcoin (`bitcoin`)
  - Ethereum (`ethereum`)
  - Stablecoins (USDC, USDT, DAI, etc.)
  - Major altcoins
- **Data Fetched**:
  - `market_chart` → OHLCV, market cap, volume
  - Price in USD, EUR, GBP, JPY, CNY
  - 24h % change
  - Market cap rankings
- **Authentication**: None (free tier, rate-limited)
- **Rate Limiting**: 10-50 calls/minute (free)
- **Features**:
  - Historical price data
  - Volume analysis
  - Market cap trends
  - Cross-currency pricing
- **Typical Use Cases**:
  - Cryptocurrency portfolio tracking
  - Macro-correlation analysis (crypto vs. traditional assets)
  - Sentiment-driven risk assessment

---

### 4️⃣ DERIVATIVES & MARKET DEPTH

#### **4.1 Yahoo Finance Options**
- **Type**: REST API (via yfinance wrapper)
- **Module**: `modules/data_loader.py`
- **Database Table**: `options_data`
- **Data Coverage**: Listed equity options (calls, puts)
- **Frequency**: Daily (post-market)
- **SLA**: Max staleness 1 day
- **API Endpoint**: Not exposed; internal analytics
- **Data Captured**:
  - Strike prices
  - Option bid/ask
  - Open interest
  - Implied volatility
  - Greeks (delta, gamma, theta, vega)
- **Features**:
  - Implied volatility surface extraction
  - Put/call ratio analysis
  - Volatility skew monitoring
- **Typical Use Cases**:
  - Options market microstructure
  - Hedging cost analysis
  - Earnings anticipation signals

#### **4.2 ICI ETF Flows**
- **Type**: CSV Download / Web Scrape
- **Module**: `modules/ici_etf_data.py`
- **Database Tables**:
  - `ici_etf_weekly_flows` (weekly)
  - `ici_etf_flows` (monthly aggregates)
- **Data Coverage**: US mutual fund and ETF flows
- **Frequency**: Weekly/Monthly
- **SLA**: Max staleness 1 week
- **Data Tracked**:
  - ETF inflows/outflows by category
  - Mutual fund flows
  - Asset-class rotation signals
- **Features**:
  - Flow trend analysis
  - Rotation detection (equities → bonds, etc.)
  - Liquidity stress indicators

---

### 5️⃣ SENTIMENT & NEWS DATA

#### **5.1 News Sentiment (External Source)**
- **Type**: CSV Archive + Database Archive
- **Module**: `modules/sentiment_analysis.py` + `scripts/ingest_sentiment_csv_to_postgres.py`
- **Database Tables**:
  - `news_sentiment` (individual articles)
  - `sentiment_summary` (aggregated daily/ticker)
- **Data Coverage**: Financial news sentiment by ticker
- **Frequency**: Daily aggregations (near real-time ingestion)
- **SLA**: Max staleness 1 day
- **Columns Tracked**:
  - `ticker` (company symbol)
  - `headline` (news title)
  - `sentiment_score` (-1 to +1)
  - `published_date`
  - `source` (news outlet)
  - `url` (link to article)
- **Features**:
  - Article-level sentiment
  - Daily median/mean aggregation
  - Sentiment trend analysis
  - Insider trading correlation
- **Data Source Path**: `data/sentiment/` (CSV archives)

#### **5.2 Google Trends**
- **Type**: Web Scrape / pytrends
- **Module**: Not currently integrated (placeholder table: `google_trends`)
- **Database Table**: `google_trends`
- **Data Coverage**: Search volume trends for keywords
- **Frequency**: Daily
- **Features** (when integrated):
  - Search interest normalization (0-100)
  - Relative interest over time
  - Regional breakdowns
  - Related queries

---

### 6️⃣ DERIVED FEATURES & AGGREGATIONS

These are NOT primary data sources but **computed/derived features** from the above sources:

#### **6.1 Technical Indicators**
- **Module**: `modules/technical_analysis.py` + `modules/features/technical_indicators.py`
- **Database Table**: `technical_features`
- **Indicators Computed**:
  - Moving averages (SMA 20, 50, 200)
  - MACD (12/26/9)
  - RSI (14-period)
  - Bollinger Bands (20/2)
  - Stochastic oscillator
  - ATR (Average True Range)
  - VWAP (Volume-Weighted Average Price)
- **Dependencies**: Yahoo Finance OHLCV data

#### **6.2 Margin Call Risk Metrics**
- **Module**: `modules/features/margin_risk_composite.py`
- **Database Table**: `margin_call_risk`
- **Risk Signals Computed**:
  - Leverage ratios
  - Drawdown exposure
  - VIX regime assessment
  - Margin utilization
- **Dependencies**: Stock prices, VIX, leverage ETF data

#### **6.3 Financial Health Scores**
- **Module**: `modules/features/financial_health_scorer.py`
- **Database Table**: `financial_health_scores`
- **Scores Computed**:
  - Leverage score (debt/equity analysis via SEC 10-K)
  - Liquidity score (working capital)
  - Profitability score (margins via 10-Q)
  - Overall health grade (A-F)
- **Dependencies**: SEC filings

#### **6.4 Insider Trading Tracker**
- **Module**: `modules/features/insider_trading_tracker.py`
- **Database Table**: Derived from `sec_submissions`
- **Signals**:
  - Executive buy/sell ratio
  - Filing date anomalies
  - Transaction size analysis
  - Sentiment score aggregation
- **Dependencies**: SEC Form 4 filings

#### **6.5 Sector Rotation Detection**
- **Module**: `modules/features/sector_rotation_detector.py`
- **Database Tables**:
  - `sector_rotation_analysis`
  - `sector_relative_strength`
- **Phase Classification**:
  - Expansion (stocks rising)
  - Late expansion (momentum slowing)
  - Contraction (market declining)
  - Recovery (bottoming process)
- **Dependencies**: Sector ETF flows, market data

#### **6.6 Leverage Metrics**
- **Module**: `modules/features/leverage_metrics.py`
- **Database Table**: `leverage_metrics`
- **Metrics Tracked**:
  - Leveraged ETF flows (3x, 2x inverse)
  - Margin debt trends
  - Options positioning (put/call ratios)
  - Short-selling activity
- **Dependencies**: Yahoo Finance, options data, SEC data

---

## 🔐 Authentication & API Keys Required

### Required `.env` Variables:

```env
# FRED (required)
FRED_API_KEY=your_fred_api_key

# Census Bureau (required for EITS)
CENSUS_API_KEY=your_census_api_key

# BLS (optional, increases rate limit)
BLS_API_KEY=your_bls_api_key

# EIA (required)
EIA_API_KEY=your_eia_api_key

# Database Backend
DATABASE_BACKEND=postgresql
DATABASE_URL=postgresql://user:pass@localhost:5432/db

# FastAPI Auth
API_KEY=your_api_key_for_endpoints

# Optional: Proxy for IP rotation
PROXY_URL=http://proxy:port
```

---

## 📊 Database Schema Summary

### Core Data Tables:
- `fred_data` - 400K+ FRED time series
- `yfinance_ohlcv` - Stock OHLCV (daily)
- `options_data` - Options market data
- `cboe_vix_history` - VIX historical
- `cboe_vix_term_structure` - VIX futures
- `worldbank_indicators` - 1400+ indicators
- `imf_exchange_rates` - Currency pairs
- `imf_indicators` - IMF macroeconomic projections
- `oecd_indicators` - OECD country metrics
- `bls_data` - Labor statistics
- `census_data` - Census economic indicators
- `eia_data` - Energy data
- `news_sentiment` - Article-level sentiment
- `sentiment_summary` - Aggregated sentiment
- `google_trends` - Search trends (placeholder)

### SEC Data Tables:
- `sec_submissions` - Filing metadata
- `sec_financial_statements` - XBRL facts
- `sec_company_facts` - Normalized CIK facts
- `sec_filings` - Filing summaries
- `sec_13f_holdings` - Institutional positioning
- `sec_fails_to_deliver` - FTD data

### Derived/Computed Tables:
- `technical_features` - Technical indicators
- `margin_call_risk` - Risk metrics
- `financial_health_scores` - Health grades
- `leverage_metrics` - Leverage indicators
- `sector_rotation_analysis` - Rotation phases
- `sector_relative_strength` - Sector rankings
- `ici_etf_flows` - ETF flow data
- `ici_etf_weekly_flows` - Weekly aggregates

---

## 🔗 API Endpoints - Complete Reference

### Data Retrieval Endpoints:
```
GET /v1/data/fred                          # List FRED series
GET /v1/data/fred/{series_id}              # Get FRED series
GET /v1/data/stocks                        # List available stocks
GET /v1/data/stocks/{ticker}               # Get stock OHLCV
GET /v1/data/sec/filings/{ticker}          # Get SEC filings
GET /v1/data/sec/insider/{ticker}          # Get insider transactions
GET /v1/data/worldbank                     # Get World Bank data
GET /v1/data/imf/exchange-rates            # Get IMF exchange rates
GET /v1/data/oecd                          # Get OECD indicators
GET /v1/data/bls                           # Get BLS data
GET /v1/data/census                        # Get Census data
GET /v1/data/eia                           # Get EIA data
```

### Feature/Analysis Endpoints:
```
GET /v1/features/technical                 # Technical indicators
GET /v1/signals/margin-risk                # Margin risk scores
GET /v1/analysis/sector-rotation           # Sector rotation phase
GET /v1/analysis/financial-health/{ticker} # Financial health score
```

---

## 📈 Data Quality & Refresh Schedules

| Source | Frequency | SLA | Refresh Method |
|--------|-----------|-----|----------------|
| FRED | As published | 24h | Nightly job |
| Yahoo Finance | Daily (post-market) | 1d | Nightly job |
| SEC EDGAR | Real-time | 1h | Real-time ingestion |
| CBOE VIX | Daily (post-market) | 6h | 4x daily job |
| BLS | Monthly | 2w | Manual trigger |
| Census EITS | Weekly | 1w | Weekly job |
| EIA | Daily | 1d | Daily job |
| IMF SDMX | Quarterly | 1mo | Monthly job |
| OECD | Varies | 1mo | Monthly job |
| World Bank | Annual | 3mo | Quarterly job |
| CoinGecko | Real-time | 5min | On-demand |
| News Sentiment | Daily | 1d | Daily aggregation |
| ICI ETF Flows | Weekly | 1w | Weekly job |

---

## 🛠️ Adding a New Data Source

Follow the **5-step process** in [ADDING_DATA_SOURCES.md](ADDING_DATA_SOURCES.md):

1. **Define Source Config** in `modules/data_sources.py`
2. **Create Fetch Module** in `modules/{source_name}_data.py`
3. **Add DB Schema** to `modules/database/schema.py`
4. **Register Scheduler** in `.github/workflows/` or `services/scheduler.py`
5. **Expose via API** in `api/v1/routes/data.py`

---

## 📞 Support & Documentation

- **Architecture**: See [ARCHITECTURE_IMPLEMENTATION.md](ARCHITECTURE_IMPLEMENTATION.md)
- **Deployment**: See [DEPLOYMENT_CHECKLIST.md](DEPLOYMENT_CHECKLIST.md)
- **Data Refresh**: See [AUTOMATED_DATA_REFRESH.md](AUTOMATED_DATA_REFRESH.md)
- **Environment Setup**: See [ENVIRONMENTS.md](ENVIRONMENTS.md)

---

**Version**: 1.0  
**Maintainer**: Economic Dashboard Team  
**Last Audit**: 2026-06-11
