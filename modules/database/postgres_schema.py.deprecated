"""
PostgreSQL Schema Definitions

Defines all tables for the Economic Dashboard PostgreSQL database.
Similar to schema.py but with PostgreSQL-specific optimizations.
"""

import logging

logger = logging.getLogger(__name__)


def create_all_tables(db):
    """Create all tables in the PostgreSQL database."""
    logger.info("Initializing PostgreSQL schema...")
    
    # Core data tables
    create_fred_data_table(db)
    create_yfinance_ohlcv_table(db)
    create_options_data_table(db)
    create_ici_etf_weekly_flows_table(db)
    create_ici_etf_flows_table(db)
    create_market_indicators_table(db)
    create_cboe_vix_history_table(db)
    create_cboe_vix_term_structure_table(db)
    
    # Feature tables
    create_technical_features_table(db)
    create_derived_features_table(db)
    
    # ML tables
    create_ml_predictions_table(db)
    create_model_performance_table(db)
    create_feature_importance_table(db)
    
    # System tables
    create_data_refresh_log_table(db)
    create_data_retention_policy_table(db)
    
    # SEC tables
    create_sec_filings_table(db)
    create_sec_company_facts_table(db)
    create_sec_fails_to_deliver_table(db)
    
    logger.info("PostgreSQL schema initialized successfully")


def create_fred_data_table(db):
    """Create table for FRED economic data."""
    db.execute("""
        CREATE TABLE IF NOT EXISTS fred_data (
            series_id VARCHAR(100) NOT NULL,
            date DATE NOT NULL,
            value DOUBLE PRECISION,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (series_id, date)
        )
    """)
    
    db.execute("CREATE INDEX IF NOT EXISTS idx_fred_series ON fred_data(series_id)")
    db.execute("CREATE INDEX IF NOT EXISTS idx_fred_date ON fred_data(date)")
    logger.info("Created table: fred_data")


def create_yfinance_ohlcv_table(db):
    """Create table for stock OHLCV data."""
    db.execute("""
        CREATE TABLE IF NOT EXISTS yfinance_ohlcv (
            ticker VARCHAR(20) NOT NULL,
            date DATE NOT NULL,
            open DOUBLE PRECISION,
            high DOUBLE PRECISION,
            low DOUBLE PRECISION,
            close DOUBLE PRECISION,
            volume BIGINT,
            adj_close DOUBLE PRECISION,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (ticker, date)
        )
    """)
    
    db.execute("CREATE INDEX IF NOT EXISTS idx_yf_ticker ON yfinance_ohlcv(ticker)")
    db.execute("CREATE INDEX IF NOT EXISTS idx_yf_date ON yfinance_ohlcv(date)")
    db.execute("CREATE INDEX IF NOT EXISTS idx_yf_ticker_date ON yfinance_ohlcv(ticker, date)")
    logger.info("Created table: yfinance_ohlcv")


def create_options_data_table(db):
    """Create table for options data."""
    db.execute("""
        CREATE TABLE IF NOT EXISTS options_data (
            ticker VARCHAR(20) NOT NULL,
            date DATE NOT NULL,
            expiration_date DATE NOT NULL,
            put_volume BIGINT,
            call_volume BIGINT,
            put_open_interest BIGINT,
            call_open_interest BIGINT,
            put_call_volume_ratio DOUBLE PRECISION,
            put_call_oi_ratio DOUBLE PRECISION,
            total_put_iv DOUBLE PRECISION,
            total_call_iv DOUBLE PRECISION,
            iv_rank DOUBLE PRECISION,
            iv_percentile DOUBLE PRECISION,
            skew DOUBLE PRECISION,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (ticker, date, expiration_date)
        )
    """)
    
    db.execute("CREATE INDEX IF NOT EXISTS idx_options_ticker ON options_data(ticker)")
    db.execute("CREATE INDEX IF NOT EXISTS idx_options_date ON options_data(date)")
    logger.info("Created table: options_data")


def create_ici_etf_weekly_flows_table(db):
    """Create table for ICI weekly ETF flow statistics."""
    db.execute("""
        CREATE TABLE IF NOT EXISTS ici_etf_weekly_flows (
            week_ending DATE NOT NULL,
            fund_type VARCHAR(100) NOT NULL,
            estimated_flows DOUBLE PRECISION,
            total_net_assets DOUBLE PRECISION,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (week_ending, fund_type)
        )
    """)

    db.execute("CREATE INDEX IF NOT EXISTS idx_ici_week_end ON ici_etf_weekly_flows(week_ending)")
    db.execute("CREATE INDEX IF NOT EXISTS idx_ici_week_fund ON ici_etf_weekly_flows(fund_type)")
    logger.info("Created table: ici_etf_weekly_flows")


def create_ici_etf_flows_table(db):
    """Create table for ICI monthly ETF flow statistics."""
    db.execute("""
        CREATE TABLE IF NOT EXISTS ici_etf_flows (
            date DATE NOT NULL,
            fund_category VARCHAR(100) NOT NULL,
            net_new_cash_flow DOUBLE PRECISION,
            net_issuance DOUBLE PRECISION,
            redemptions DOUBLE PRECISION,
            reinvested_dividends DOUBLE PRECISION,
            total_net_assets DOUBLE PRECISION,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (date, fund_category)
        )
    """)

    db.execute("CREATE INDEX IF NOT EXISTS idx_ici_month_date ON ici_etf_flows(date)")
    db.execute("CREATE INDEX IF NOT EXISTS idx_ici_month_category ON ici_etf_flows(fund_category)")
    logger.info("Created table: ici_etf_flows")


def create_market_indicators_table(db):
    """Create table for market-level indicators."""
    db.execute("""
        CREATE TABLE IF NOT EXISTS market_indicators (
            date DATE NOT NULL,
            vix DOUBLE PRECISION,
            vix_3m DOUBLE PRECISION,
            vvix DOUBLE PRECISION,
            skew DOUBLE PRECISION,
            put_call_ratio DOUBLE PRECISION,
            high_yield_spread DOUBLE PRECISION,
            term_spread DOUBLE PRECISION,
            credit_spread DOUBLE PRECISION,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (date)
        )
    """)
    
    db.execute("CREATE INDEX IF NOT EXISTS idx_market_date ON market_indicators(date)")
    logger.info("Created table: market_indicators")


def create_cboe_vix_history_table(db):
    """Create table for raw CBOE VIX OHLC data."""
    db.execute("""
        CREATE TABLE IF NOT EXISTS cboe_vix_history (
            date DATE NOT NULL,
            open DOUBLE PRECISION,
            high DOUBLE PRECISION,
            low DOUBLE PRECISION,
            close DOUBLE PRECISION,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (date)
        )
    """)

    db.execute("CREATE INDEX IF NOT EXISTS idx_cboe_vix_date ON cboe_vix_history(date)")
    logger.info("Created table: cboe_vix_history")


def create_cboe_vix_term_structure_table(db):
    """Create table for CBOE VIX futures term structure."""
    db.execute("""
        CREATE TABLE IF NOT EXISTS cboe_vix_term_structure (
            date DATE NOT NULL,
            expiration_date DATE,
            days_to_expiration INTEGER,
            contract_symbol VARCHAR(50),
            settlement DOUBLE PRECISION,
            vix_index DOUBLE PRECISION,
            basis DOUBLE PRECISION,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (date, days_to_expiration)
        )
    """)

    db.execute("CREATE INDEX IF NOT EXISTS idx_cboe_vix_term_date ON cboe_vix_term_structure(date)")
    db.execute("CREATE INDEX IF NOT EXISTS idx_cboe_vix_term_expiration ON cboe_vix_term_structure(expiration_date)")
    logger.info("Created table: cboe_vix_term_structure")


def create_technical_features_table(db):
    """Create table for technical analysis features."""
    db.execute("""
        CREATE TABLE IF NOT EXISTS technical_features (
            ticker VARCHAR(20) NOT NULL,
            date DATE NOT NULL,
            -- Momentum indicators
            rsi_14 DOUBLE PRECISION,
            rsi_28 DOUBLE PRECISION,
            stoch_k DOUBLE PRECISION,
            stoch_d DOUBLE PRECISION,
            williams_r DOUBLE PRECISION,
            roc_10 DOUBLE PRECISION,
            roc_20 DOUBLE PRECISION,
            -- Trend indicators
            sma_20 DOUBLE PRECISION,
            sma_50 DOUBLE PRECISION,
            sma_200 DOUBLE PRECISION,
            ema_12 DOUBLE PRECISION,
            ema_26 DOUBLE PRECISION,
            macd DOUBLE PRECISION,
            macd_signal DOUBLE PRECISION,
            macd_hist DOUBLE PRECISION,
            adx DOUBLE PRECISION,
            -- Volatility indicators
            bb_upper DOUBLE PRECISION,
            bb_middle DOUBLE PRECISION,
            bb_lower DOUBLE PRECISION,
            bb_width DOUBLE PRECISION,
            atr_14 DOUBLE PRECISION,
            -- Volume indicators
            obv DOUBLE PRECISION,
            obv_ema DOUBLE PRECISION,
            mfi DOUBLE PRECISION,
            -- Price action
            returns_1d DOUBLE PRECISION,
            returns_5d DOUBLE PRECISION,
            returns_20d DOUBLE PRECISION,
            volatility_20d DOUBLE PRECISION,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (ticker, date)
        )
    """)
    
    db.execute("CREATE INDEX IF NOT EXISTS idx_tech_ticker ON technical_features(ticker)")
    db.execute("CREATE INDEX IF NOT EXISTS idx_tech_date ON technical_features(date)")
    logger.info("Created table: technical_features")


def create_derived_features_table(db):
    """Create table for derived/cross-asset features."""
    db.execute("""
        CREATE TABLE IF NOT EXISTS derived_features (
            ticker VARCHAR(20) NOT NULL,
            date DATE NOT NULL,
            -- Market regime
            regime VARCHAR(50),
            regime_score DOUBLE PRECISION,
            -- Relative strength
            vs_spy_return DOUBLE PRECISION,
            vs_sector_return DOUBLE PRECISION,
            beta_60d DOUBLE PRECISION,
            -- Sentiment proxies
            vix_level VARCHAR(20),
            term_spread_level VARCHAR(20),
            -- Z-scores
            rsi_zscore DOUBLE PRECISION,
            volume_zscore DOUBLE PRECISION,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (ticker, date)
        )
    """)
    
    db.execute("CREATE INDEX IF NOT EXISTS idx_derived_ticker ON derived_features(ticker)")
    db.execute("CREATE INDEX IF NOT EXISTS idx_derived_date ON derived_features(date)")
    logger.info("Created table: derived_features")


def create_ml_predictions_table(db):
    """Create table for ML model predictions."""
    db.execute("""
        CREATE TABLE IF NOT EXISTS ml_predictions (
            ticker VARCHAR(20) NOT NULL,
            prediction_date DATE NOT NULL,
            target_date DATE NOT NULL,
            horizon_days INTEGER NOT NULL,
            model_name VARCHAR(100) NOT NULL,
            predicted_return DOUBLE PRECISION,
            predicted_direction INTEGER,
            confidence DOUBLE PRECISION,
            feature_version VARCHAR(50),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (ticker, prediction_date, target_date, model_name)
        )
    """)
    
    db.execute("CREATE INDEX IF NOT EXISTS idx_pred_ticker ON ml_predictions(ticker)")
    db.execute("CREATE INDEX IF NOT EXISTS idx_pred_date ON ml_predictions(prediction_date)")
    db.execute("CREATE INDEX IF NOT EXISTS idx_pred_model ON ml_predictions(model_name)")
    logger.info("Created table: ml_predictions")


def create_model_performance_table(db):
    """Create table for model performance metrics."""
    db.execute("""
        CREATE TABLE IF NOT EXISTS model_performance (
            model_name VARCHAR(100) NOT NULL,
            evaluation_date DATE NOT NULL,
            horizon_days INTEGER NOT NULL,
            metric_name VARCHAR(50) NOT NULL,
            metric_value DOUBLE PRECISION,
            sample_size INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (model_name, evaluation_date, horizon_days, metric_name)
        )
    """)
    
    db.execute("CREATE INDEX IF NOT EXISTS idx_perf_model ON model_performance(model_name)")
    db.execute("CREATE INDEX IF NOT EXISTS idx_perf_date ON model_performance(evaluation_date)")
    logger.info("Created table: model_performance")


def create_feature_importance_table(db):
    """Create table for feature importance tracking."""
    db.execute("""
        CREATE TABLE IF NOT EXISTS feature_importance (
            model_name VARCHAR(100) NOT NULL,
            training_date DATE NOT NULL,
            feature_name VARCHAR(100) NOT NULL,
            importance_score DOUBLE PRECISION,
            importance_rank INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (model_name, training_date, feature_name)
        )
    """)
    
    db.execute("CREATE INDEX IF NOT EXISTS idx_feat_imp_model ON feature_importance(model_name)")
    db.execute("CREATE INDEX IF NOT EXISTS idx_feat_imp_date ON feature_importance(training_date)")
    logger.info("Created table: feature_importance")


def create_data_refresh_log_table(db):
    """Create table for tracking data refresh operations."""
    db.execute("""
        CREATE TABLE IF NOT EXISTS data_refresh_log (
            id SERIAL PRIMARY KEY,
            source VARCHAR(100) NOT NULL,
            refresh_type VARCHAR(50),
            start_time TIMESTAMP NOT NULL,
            end_time TIMESTAMP,
            status VARCHAR(20),
            records_processed INTEGER,
            error_message TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    db.execute("CREATE INDEX IF NOT EXISTS idx_refresh_source ON data_refresh_log(source)")
    db.execute("CREATE INDEX IF NOT EXISTS idx_refresh_time ON data_refresh_log(start_time)")
    logger.info("Created table: data_refresh_log")


def create_data_retention_policy_table(db):
    """Create table for data retention policies."""
    db.execute("""
        CREATE TABLE IF NOT EXISTS data_retention_policy (
            table_name VARCHAR(100) PRIMARY KEY,
            retention_days INTEGER NOT NULL,
            last_cleanup TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    logger.info("Created table: data_retention_policy")


def create_sec_filings_table(db):
    """Create table for SEC filing metadata."""
    db.execute("""
        CREATE TABLE IF NOT EXISTS sec_filings (
            accession_number VARCHAR(50) PRIMARY KEY,
            cik VARCHAR(20) NOT NULL,
            company_name VARCHAR(200),
            form_type VARCHAR(20),
            filing_date DATE,
            report_date DATE,
            file_url TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    db.execute("CREATE INDEX IF NOT EXISTS idx_sec_filings_cik ON sec_filings(cik)")
    db.execute("CREATE INDEX IF NOT EXISTS idx_sec_filings_form ON sec_filings(form_type)")
    db.execute("CREATE INDEX IF NOT EXISTS idx_sec_filings_date ON sec_filings(filing_date)")
    logger.info("Created table: sec_filings")


def create_sec_company_facts_table(db):
    """Create table for SEC company facts (financial data)."""
    db.execute("""
        CREATE TABLE IF NOT EXISTS sec_company_facts (
            cik VARCHAR(20) NOT NULL,
            fact_name VARCHAR(100) NOT NULL,
            fact_label VARCHAR(200),
            fiscal_year INTEGER,
            fiscal_period VARCHAR(10),
            end_date DATE,
            value DOUBLE PRECISION,
            units VARCHAR(50),
            form VARCHAR(20),
            filed_date DATE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (cik, fact_name, fiscal_year, fiscal_period)
        )
    """)
    
    db.execute("CREATE INDEX IF NOT EXISTS idx_sec_facts_cik ON sec_company_facts(cik)")
    db.execute("CREATE INDEX IF NOT EXISTS idx_sec_facts_name ON sec_company_facts(fact_name)")
    db.execute("CREATE INDEX IF NOT EXISTS idx_sec_facts_date ON sec_company_facts(end_date)")
    logger.info("Created table: sec_company_facts")


def create_sec_fails_to_deliver_table(db):
    """Create table for SEC fails-to-deliver data."""
    db.execute("""
        CREATE TABLE IF NOT EXISTS sec_fails_to_deliver (
            settlement_date DATE NOT NULL,
            cusip VARCHAR(20) NOT NULL,
            symbol VARCHAR(20),
            quantity BIGINT,
            description TEXT,
            price DOUBLE PRECISION,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (settlement_date, cusip)
        )
    """)
    
    db.execute("CREATE INDEX IF NOT EXISTS idx_ftd_symbol ON sec_fails_to_deliver(symbol)")
    db.execute("CREATE INDEX IF NOT EXISTS idx_ftd_date ON sec_fails_to_deliver(settlement_date)")
    logger.info("Created table: sec_fails_to_deliver")
