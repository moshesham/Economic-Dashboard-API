# Data Products & Data Sources Catalog - Economic Dashboard API

**Date:** December 2025  
**Version:** 2.0  
**Status:** Technical Planning Document

---

## Table of Contents

1. [Overview](#overview)
2. [Free & Open Data Sources](#free--open-data-sources)
3. [Data Products Catalog](#data-products-catalog)
4. [Data Exposure Methods](#data-exposure-methods)
5. [Technical Implementation](#technical-implementation)
6. [Data Quality & Governance](#data-quality--governance)

---

## Overview

This document catalogs available free and open data sources that can be integrated into the Economic Dashboard API, and defines the data products that can be built from these sources. The focus is on **publicly available, high-quality datasets** that provide value for economic analysis, financial research, and data-driven decision making.

### Guiding Principles

1. **Free & Open First**: Prioritize publicly available data sources (government agencies, international organizations)
2. **Quality Over Quantity**: Focus on authoritative sources with proper documentation
3. **Sustainability**: Use data sources with long-term availability and support
4. **Interoperability**: Combine multiple sources to create enriched data products
5. **Transparency**: Clear data lineage and source attribution

---

## Free & Open Data Sources

### 🌍 International Organizations

#### 1. World Bank Open Data
**URL:** https://data.worldbank.org/  
**API:** https://datahelpdesk.worldbank.org/knowledgebase/topics/125589

**Available Data:**
- **Development Indicators**: 1,400+ time series covering 217 economies
  - GDP, GNI, population, trade, debt, infrastructure
  - Education, health, environment metrics
  - Poverty, inequality, employment statistics
- **Historical Coverage**: 1960-present (varies by indicator)
- **Update Frequency**: Quarterly to annually
- **Format**: API (JSON, XML), CSV, Excel

**Priority Datasets:**
```
GDP (NY.GDP.MKTP.CD)
GDP growth (NY.GDP.MKTP.KD.ZG)
Population (SP.POP.TOTL)
Inflation, consumer prices (FP.CPI.TOTL.ZG)
Trade (% of GDP) (NE.TRD.GNFS.ZS)
Foreign direct investment (BX.KLT.DINV.CD.WD)
Government debt (GC.DOD.TOTL.GD.ZS)
Unemployment (SL.UEM.TOTL.ZS)
```

**Integration Status:** 🟡 To be implemented

---

#### 2. International Monetary Fund (IMF)
**URL:** https://data.imf.org/  
**API:** https://datahelp.imf.org/knowledgebase/articles/667681

**Available Data:**
- **International Financial Statistics (IFS)**: Exchange rates, interest rates, prices
- **World Economic Outlook (WEO)**: GDP, inflation, fiscal data for 190+ countries
- **Balance of Payments (BOP)**: Trade, capital flows, reserves
- **Government Finance Statistics (GFS)**: Revenue, expenditure, debt
- **Primary Commodity Prices**: Oil, metals, agriculture

**Priority Datasets:**
```
Exchange rates (bilateral and effective)
Interest rates (policy rates, treasury yields)
Reserve assets
Current account balance
General government debt
Commodity price indices
```

**Integration Status:** 🟡 To be implemented

---

#### 3. OECD Data
**URL:** https://data.oecd.org/  
**API:** https://data.oecd.org/api/

**Available Data:**
- **Economic Indicators**: GDP, CPI, unemployment, trade for 38 member countries
- **Leading Indicators**: Composite leading indicator (CLI), business confidence
- **Productivity**: Labor productivity, multi-factor productivity
- **Innovation**: R&D expenditure, patents, technology adoption
- **Social Indicators**: Education, health, inequality

**Priority Datasets:**
```
Composite Leading Indicator (MEI_CLI)
GDP forecast (EO)
Unemployment rate (MEI_ARCHIVE)
Consumer Price Index (MEI_ARCHIVE)
Short-term interest rates (MEI_FIN)
```

**Integration Status:** 🟡 To be implemented

---

#### 4. United Nations (UN) Data
**URL:** https://data.un.org/  
**API:** http://data.un.org/Host.aspx?Content=API

**Available Data:**
- **UN Comtrade**: International trade statistics (5.9 billion records)
- **UN National Accounts**: GDP, consumption, investment by country
- **Population Division**: Population estimates and projections
- **Sustainable Development Goals (SDG)**: 230+ indicators

**Priority Datasets:**
```
Trade flows (imports/exports by commodity)
National accounts aggregates
Population by age and gender
SDG indicators (poverty, health, education)
```

**Integration Status:** 🟡 To be implemented

---

### 🏦 Central Banks & Government Agencies

#### 5. Federal Reserve Economic Data (FRED)
**URL:** https://fred.stlouisfed.org/  
**API:** https://fred.stlouisfed.org/docs/api/fred/

**Available Data:**
- **800,000+ time series** from 100+ sources
- **US Economic Data**: GDP, CPI, unemployment, industrial production
- **Financial Markets**: Interest rates, exchange rates, stock indices
- **Regional Data**: State-level employment, housing, income

**Priority Datasets:**
```
GDP (GDP)
Unemployment Rate (UNRATE)
CPI (CPIAUCSL)
Federal Funds Rate (FEDFUNDS)
10-Year Treasury (DGS10)
S&P 500 (SP500)
Dollar Index (DTWEXBGS)
```

**Integration Status:** ✅ Already implemented

---

#### 6. European Central Bank (ECB)
**URL:** https://data.ecb.europa.eu/  
**API:** https://data.ecb.europa.eu/help/api/overview

**Available Data:**
- **Monetary Policy**: Interest rates, money supply, credit
- **Exchange Rates**: EUR/USD, EUR/GBP, etc.
- **Financial Markets**: Bond yields, stock indices
- **Economic Statistics**: GDP, inflation, trade for Eurozone

**Priority Datasets:**
```
ECB policy rates
EUR exchange rates
Eurozone GDP
Harmonized CPI
Bank lending rates
```

**Integration Status:** 🟡 To be implemented

---

#### 7. Bank for International Settlements (BIS)
**URL:** https://www.bis.org/statistics/  
**API:** https://www.bis.org/statistics/api_aboutus.htm

**Available Data:**
- **Credit Statistics**: Total credit to non-financial sector
- **Debt Securities**: International debt issuance
- **Exchange Rates**: Effective exchange rate indices
- **Property Prices**: Residential and commercial real estate

**Priority Datasets:**
```
Total credit to private non-financial sector
Credit-to-GDP gaps
Debt service ratios
Effective exchange rates (real and nominal)
Residential property prices
```

**Integration Status:** 🟡 To be implemented

---

### 📊 Market & Financial Data

#### 8. Yahoo Finance
**URL:** https://finance.yahoo.com/  
**API:** Public endpoints (unofficial)

**Available Data:**
- **Stock Prices**: Daily OHLCV for global equities
- **Indices**: S&P 500, NASDAQ, Dow Jones, international indices
- **ETFs**: 3,000+ ETFs
- **Currency**: 150+ currency pairs
- **Commodities**: Gold, oil, metals

**Priority Datasets:**
```
Major US indices (SPY, QQQ, DIA)
Sector ETFs (XLF, XLE, XLK, XLV, etc.)
International indices (EEM, EFA)
Currency pairs (EURUSD, USDJPY, etc.)
Gold (GLD), Oil (USO)
```

**Integration Status:** ✅ Already implemented (via yfinance)

---

#### 9. CBOE (Volatility Data)
**URL:** https://www.cboe.com/  
**API:** Public data downloads

**Available Data:**
- **VIX Index**: Market volatility indicator
- **VIX Futures**: Term structure
- **Options Volume**: Put/call ratios
- **Skew Indices**: Market sentiment

**Priority Datasets:**
```
VIX Index (real-time and historical)
VIX futures term structure
VIX9D (9-day volatility)
VVIX (volatility of volatility)
SKEW (tail risk)
```

**Integration Status:** ✅ Already implemented

---

#### 10. Quandl/Nasdaq Data Link (Free Datasets)
**URL:** https://data.nasdaq.com/  
**API:** https://docs.data.nasdaq.com/

**Available Free Data:**
- **WIKI Prices**: End-of-day stock prices (historical, no longer updated)
- **FRED**: Integration with Federal Reserve data
- **Cryptocurrency**: Bitcoin, Ethereum prices
- **Commodities**: Gold, silver, oil (historical)

**Priority Datasets:**
```
Bitcoin price (BCHAIN/MKPRU)
Ethereum price
Gold price (LBMA/GOLD)
WTI Crude oil
```

**Integration Status:** 🟡 To be implemented

---

### 🏢 Alternative & Specialty Data

#### 11. SEC EDGAR
**URL:** https://www.sec.gov/edgar  
**API:** https://www.sec.gov/developer

**Available Data:**
- **Company Filings**: 10-K, 10-Q, 8-K, proxy statements
- **Insider Trading**: Form 4 filings
- **Institutional Holdings**: 13F filings
- **Fails-to-Deliver**: Short sale data

**Priority Datasets:**
```
Form 4 (insider transactions)
13F (institutional holdings)
Fails-to-deliver
Company financials (XBRL data)
```

**Integration Status:** ✅ Partially implemented

---

#### 12. US Bureau of Labor Statistics (BLS)
**URL:** https://www.bls.gov/  
**API:** https://www.bls.gov/developers/

**Available Data:**
- **Employment**: Nonfarm payrolls, unemployment, labor force
- **Prices**: CPI, PPI, import/export prices
- **Compensation**: Wages, benefits, productivity
- **Consumer Spending**: Consumer Expenditure Survey

**Priority Datasets:**
```
Nonfarm Payrolls (CES0000000001)
Unemployment Rate (LNS14000000)
CPI-U (CUUR0000SA0)
Average Hourly Earnings (CES0500000003)
```

**Integration Status:** 🟡 To be implemented (overlap with FRED)

---

#### 13. US Census Bureau
**URL:** https://www.census.gov/  
**API:** https://www.census.gov/data/developers.html

**Available Data:**
- **Economic Indicators**: Retail sales, housing starts, construction
- **International Trade**: Exports, imports by country/commodity
- **Business Statistics**: Quarterly Services Survey, Annual Business Survey
- **Demographics**: Population estimates, migration

**Priority Datasets:**
```
Advance Monthly Retail Sales
New Residential Construction (housing starts)
Monthly Trade Statistics
Quarterly E-Commerce Sales
```

**Integration Status:** 🟡 To be implemented

---

#### 14. Energy Information Administration (EIA)
**URL:** https://www.eia.gov/  
**API:** https://www.eia.gov/opendata/

**Available Data:**
- **Petroleum**: Crude oil prices, inventories, production
- **Natural Gas**: Prices, storage, consumption
- **Electricity**: Generation, consumption by source
- **Renewable Energy**: Solar, wind capacity and generation

**Priority Datasets:**
```
WTI Crude Oil Price
Crude Oil Inventories
Natural Gas Prices
Gasoline Prices
Total Energy Consumption
```

**Integration Status:** 🟡 To be implemented

---

#### 15. News & Sentiment Data (Free Sources)

**NewsAPI.org** (Free Tier)
- **Coverage**: 150,000+ sources
- **Free Tier**: 100 requests/day, 1-month history
- **Status:** ✅ Already implemented

**Reddit API** (Free)
- **Subreddits**: r/wallstreetbets, r/stocks, r/investing
- **Data**: Posts, comments, sentiment
- **Status:** 🟡 To be implemented

**Twitter/X API** (Limited Free)
- **Data**: Tweets, trends, sentiment
- **Free Tier**: Limited access
- **Status:** 🟡 To be implemented

---

### 📈 Calculated & Derived Data

#### 16. Investment Company Institute (ICI)
**URL:** https://www.ici.org/  
**Data:** Weekly ETF flows, mutual fund statistics

**Available Data:**
- **ETF Flows**: Weekly creation/redemption
- **Mutual Fund Assets**: By category
- **Money Market Funds**: Assets and yields

**Integration Status:** ✅ Already implemented

---

#### 17. Federal Reserve (Additional)
**H.4.1 Release**: Federal Reserve Balance Sheet  
**H.15 Release**: Selected Interest Rates  
**Z.1 Release**: Financial Accounts (Flow of Funds)

**Priority Datasets:**
```
Federal Reserve Assets
Treasuries held by Fed
Mortgage-backed securities holdings
Household net worth
Corporate debt outstanding
```

**Integration Status:** 🟡 To be implemented (available via FRED)

---

## Data Products Catalog

Based on the free data sources above, we can build the following data products:

### 1. 🌍 Global Economic Indicators

**Description:** Comprehensive economic indicators for 200+ countries combining World Bank, IMF, OECD, and UN data.

**Data Sources:**
- World Bank: GDP, population, trade, debt
- IMF: Exchange rates, reserves, fiscal data
- OECD: Leading indicators, productivity
- UN: Trade flows, population

**Features:**
- Unified API for cross-country comparisons
- Harmonized time series (quarterly/annually)
- YoY and QoQ growth rates
- Regional aggregations (OECD, G7, G20, EM)

**Technical Specs:**
- Update frequency: Quarterly
- Historical coverage: 1960-present
- Countries: 217
- Indicators: 1,000+

**Use Cases:**
- Cross-country economic analysis
- Development economics research
- Global macro forecasting
- Country risk assessment

---

### 2. 📊 US Economic Dashboard

**Description:** Real-time and historical US economic data from FRED, BLS, Census Bureau.

**Data Sources:**
- FRED: 800K+ time series
- BLS: Employment, CPI, wages
- Census: Retail sales, housing, trade

**Features:**
- Daily updates for high-frequency indicators
- Nowcasting for GDP, employment
- Recession probability model
- Leading economic index

**Technical Specs:**
- Update frequency: Daily to monthly
- Historical coverage: 1940s-present
- Series: 1,000+ curated indicators
- Latency: <1 hour after release

**Use Cases:**
- Economic forecasting
- Investment research
- Policy analysis
- Academic research

---

### 3. 💹 Market Data & Volatility

**Description:** Stock, ETF, commodity, and currency data with volatility metrics.

**Data Sources:**
- Yahoo Finance: OHLCV data
- CBOE: VIX, volatility indices
- Quandl: Cryptocurrency, commodities

**Features:**
- Daily OHLCV for 10,000+ securities
- Real-time volatility indices
- Options-implied volatility
- Correlation matrices

**Technical Specs:**
- Update frequency: Daily (EOD)
- Historical coverage: 20+ years
- Securities: 10,000+
- Latency: <30 min after market close

**Use Cases:**
- Algorithmic trading
- Risk management
- Portfolio optimization
- Volatility trading

---

### 4. 📈 Technical Indicators & Signals

**Description:** Pre-calculated technical indicators for stocks, indices, and ETFs.

**Data Sources:**
- Yahoo Finance (price data)
- CBOE (volatility data)

**Features:**
- 20+ technical indicators (RSI, MACD, Bollinger Bands, etc.)
- Customizable parameters
- Signal generation (buy/sell)
- Backtesting support

**Technical Specs:**
- Update frequency: Daily
- Historical coverage: 10+ years
- Indicators: 20+
- Computation time: <1 second per symbol

**Use Cases:**
- Technical analysis
- Trading strategy development
- Signal backtesting
- Educational purposes

---

### 5. 🏦 Central Bank Policy Tracker

**Description:** Centralized database of central bank policy decisions and statements.

**Data Sources:**
- Federal Reserve (FRED, official releases)
- ECB (official data)
- Bank of England, Bank of Japan, etc. (web scraping)

**Features:**
- Policy rate changes
- Quantitative easing programs
- Forward guidance analysis
- Meeting minutes sentiment

**Technical Specs:**
- Update frequency: Real-time (on announcements)
- Historical coverage: 2000-present
- Central banks: 10+ major banks
- Latency: <5 minutes after announcement

**Use Cases:**
- Monetary policy research
- FX trading
- Bond market analysis
- Economic forecasting

---

### 6. 🌐 Commodity & Energy Dashboard

**Description:** Real-time and historical commodity prices and energy data.

**Data Sources:**
- EIA: Oil, gas, electricity
- IMF: Commodity price indices
- Quandl: Metals, agriculture
- Yahoo Finance: ETFs (GLD, USO, etc.)

**Features:**
- Spot prices for major commodities
- Inventories and supply data
- Production statistics
- Price forecasts

**Technical Specs:**
- Update frequency: Daily to weekly
- Historical coverage: 30+ years
- Commodities: 50+
- Latency: <1 day

**Use Cases:**
- Commodity trading
- Inflation forecasting
- Energy policy analysis
- Supply chain planning

---

### 7. 📰 News Sentiment & Alternative Data

**Description:** Aggregated news sentiment and social media analytics.

**Data Sources:**
- NewsAPI: Financial news
- Reddit API: r/wallstreetbets, r/stocks
- Twitter API: $cashtags, trending topics

**Features:**
- Real-time sentiment scores
- Entity recognition (stocks, sectors, people)
- Trending topics detection
- Event impact analysis

**Technical Specs:**
- Update frequency: Real-time (15-min delay)
- Historical coverage: 3+ years
- Sources: 1,000+
- Latency: <15 minutes

**Use Cases:**
- Sentiment-driven trading
- Event detection
- Risk monitoring
- Research correlation with prices

---

### 8. 🏢 Corporate Fundamentals & Insider Activity

**Description:** SEC filings, insider transactions, and institutional holdings.

**Data Sources:**
- SEC EDGAR: 10-K, 10-Q, Form 4, 13F
- Yahoo Finance: Company profiles

**Features:**
- Insider transaction tracking
- Institutional ownership changes
- Financial statement data (XBRL)
- Fails-to-deliver monitoring

**Technical Specs:**
- Update frequency: Real-time (filings)
- Historical coverage: 10+ years
- Companies: 5,000+
- Latency: <30 minutes after filing

**Use Cases:**
- Insider trading analysis
- Fundamental analysis
- Short interest tracking
- Compliance monitoring

---

### 9. 🏘️ Real Estate & Housing Indicators

**Description:** Housing market data from Census Bureau, BIS, and FRED.

**Data Sources:**
- US Census: Housing starts, building permits
- BIS: International property prices
- FRED: Home prices (Case-Shiller, FHFA)

**Features:**
- Housing starts and sales
- Mortgage rates
- Home price indices
- Rental vacancy rates

**Technical Specs:**
- Update frequency: Monthly
- Historical coverage: 40+ years
- Geographies: US + 50 countries
- Latency: <1 week after release

**Use Cases:**
- Real estate investment
- Economic forecasting
- Housing policy analysis
- Mortgage modeling

---

### 10. 🔬 Innovation & Productivity Metrics

**Description:** R&D, patents, productivity data from OECD and BLS.

**Data Sources:**
- OECD: R&D expenditure, patents
- BLS: Labor productivity
- World Bank: High-tech exports

**Features:**
- R&D spending by sector
- Patent filings by technology
- Labor productivity growth
- Total factor productivity

**Technical Specs:**
- Update frequency: Annually
- Historical coverage: 20+ years
- Countries: 38 (OECD)
- Latency: 6-12 months (official data)

**Use Cases:**
- Innovation policy research
- Sector analysis
- Productivity forecasting
- Technology adoption studies

---

## Data Exposure Methods

### 1. REST API ✅ (Current)
**Status:** Implemented  
**Endpoints:** `/v1/data/{source}`

### 2. Bulk Downloads 🟡 (Planned)
**Status:** To be implemented  
**Formats:** CSV, Parquet, JSON  
**Endpoints:** `/v1/export/{dataset}`

### 3. Python SDK 🟡 (Planned)
**Status:** To be implemented  
**Package:** `economic-dashboard-python`

### 4. Data Catalog UI 🟡 (Planned)
**Status:** To be implemented  
**Features:** Browse datasets, preview data, documentation

### 5. GraphQL API 🔴 (Future)
**Status:** Future consideration  
**Benefit:** Flexible querying across multiple datasets

---

## Technical Implementation

### Integration Priority Matrix

| Data Source | Priority | Effort | Value | Status |
|-------------|----------|--------|-------|--------|
| World Bank | HIGH | Medium | High | 🟡 Planned |
| IMF | HIGH | Medium | High | 🟡 Planned |
| OECD | MEDIUM | Medium | Medium | 🟡 Planned |
| BLS | MEDIUM | Low | Medium | 🟡 Planned |
| Census Bureau | MEDIUM | Low | Medium | 🟡 Planned |
| EIA | MEDIUM | Low | Medium | 🟡 Planned |
| ECB | LOW | Medium | Low | 🔴 Future |
| BIS | LOW | Medium | Medium | 🔴 Future |
| Quandl | LOW | Low | Low | 🔴 Future |
| Reddit API | LOW | Medium | Low | 🔴 Future |

### Implementation Steps

For each new data source:

1. **Research & Planning**
   - Review API documentation
   - Identify key datasets
   - Determine update frequency
   - Check rate limits

2. **Data Source Module** (`modules/data_sources.py`)
   - Register source configuration
   - Define SLA and frequency

3. **HTTP Client** (`etl/sources/{source_name}.py`)
   - Implement fetch function
   - Handle pagination
   - Implement rate limiting
   - Add error handling

4. **Database Schema**
   - Define table structure
   - Add to `modules/database/models.py`
   - Create migration

5. **Validation** (`modules/validation.py`)
   - Define Pandera schema
   - Add data quality checks

6. **API Endpoint** (`api/v1/routes/data.py`)
   - Add GET endpoint
   - Add request/response models
   - Add documentation

7. **Scheduler** (`services/scheduler.py`)
   - Add scheduled job
   - Configure frequency

8. **Documentation**
   - Update this catalog
   - Add usage examples
   - Document limitations

---

## Data Quality & Governance

### Data Quality Metrics

For each data source, track:

- **Completeness**: % of expected data received
- **Timeliness**: Average delay from source release
- **Accuracy**: Validation pass rate
- **Availability**: Uptime of source API

### Data Lineage

Every data point includes:
```json
{
  "source": "World Bank",
  "dataset": "WDI",
  "indicator": "NY.GDP.MKTP.CD",
  "methodology": "Current US dollars",
  "last_updated": "2024-12-01",
  "ingestion_timestamp": "2024-12-24T10:00:00Z"
}
```

### Source Attribution

All data must include:
- Source name and URL
- License information (public domain, CC BY, etc.)
- Recommended citation
- Terms of use

### Example Citations

**World Bank:**
```
World Bank, World Development Indicators. 
GDP (current US$) [NY.GDP.MKTP.CD]. 
Retrieved from https://data.worldbank.org/
```

**FRED:**
```
Federal Reserve Economic Data (FRED), Federal Reserve Bank of St. Louis.
Unemployment Rate [UNRATE].
Retrieved from https://fred.stlouisfed.org/series/UNRATE
```

---

## Next Steps

### Q1 2026: Phase 1 - International Data
- [ ] Implement World Bank API integration
- [ ] Implement IMF data integration
- [ ] Implement OECD data integration
- [ ] Create unified economic indicators endpoint
- [ ] Build data catalog UI (browse datasets)

### Q2 2026: Phase 2 - US Economic Data
- [ ] Implement BLS API integration
- [ ] Implement Census Bureau integration
- [ ] Implement EIA integration
- [ ] Create US economic dashboard
- [ ] Add recession probability model

### Q3 2026: Phase 3 - Alternative Data
- [ ] Implement Reddit sentiment analysis
- [ ] Enhance SEC data coverage (13F, fails-to-deliver)
- [ ] Add real estate data (housing starts, prices)
- [ ] Create alternative data dashboard

### Q4 2026: Phase 4 - Advanced Features
- [ ] Build data quality monitoring
- [ ] Implement data lineage tracking
- [ ] Create data catalog with search
- [ ] Add data export capabilities (bulk downloads)

---

## Conclusion

This catalog prioritizes **free, high-quality data sources** from authoritative organizations like the World Bank, IMF, OECD, and US government agencies. By focusing on publicly available data, we can:

1. Build comprehensive data products without licensing costs
2. Ensure long-term sustainability and reliability
3. Provide value to researchers, analysts, and developers
4. Create a foundation for future premium offerings

The phased implementation approach allows us to incrementally add value while maintaining quality and system stability.

---

**Document Owner:** Data Engineering Team  
**Last Updated:** December 24, 2025  
**Next Review:** March 2026
