-- PostgreSQL Schema for Economic Dashboard
-- Auto-executed on first container startup via docker-entrypoint-initdb.d

-- ============================================================================
-- FRED Economic Data
-- ============================================================================
CREATE TABLE IF NOT EXISTS fred_data (
    id SERIAL PRIMARY KEY,
    series_id VARCHAR(50) NOT NULL,
    date DATE NOT NULL,
    value DOUBLE PRECISION,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(series_id, date)
);

CREATE INDEX IF NOT EXISTS idx_fred_series_date ON fred_data(series_id, date);
CREATE INDEX IF NOT EXISTS idx_fred_date ON fred_data(date);
CREATE INDEX IF NOT EXISTS idx_fred_series ON fred_data(series_id);

COMMENT ON TABLE fred_data IS 'Federal Reserve Economic Data time series';


-- ============================================================================
-- Stock Market OHLCV Data
-- ============================================================================
CREATE TABLE IF NOT EXISTS yfinance_ohlcv (
    id SERIAL PRIMARY KEY,
    ticker VARCHAR(20) NOT NULL,
    date DATE NOT NULL,
    open DOUBLE PRECISION,
    high DOUBLE PRECISION,
    low DOUBLE PRECISION,
    close DOUBLE PRECISION NOT NULL,
    volume BIGINT,
    adj_close DOUBLE PRECISION,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(ticker, date)
);

CREATE INDEX IF NOT EXISTS idx_yfinance_ticker_date ON yfinance_ohlcv(ticker, date);
CREATE INDEX IF NOT EXISTS idx_yfinance_date ON yfinance_ohlcv(date);
CREATE INDEX IF NOT EXISTS idx_yfinance_ticker ON yfinance_ohlcv(ticker);

COMMENT ON TABLE yfinance_ohlcv IS 'Yahoo Finance stock OHLCV data';


-- ============================================================================
-- CBOE VIX Historical Data
-- ============================================================================
CREATE TABLE IF NOT EXISTS cboe_vix_history (
    id SERIAL PRIMARY KEY,
    date DATE NOT NULL UNIQUE,
    open DOUBLE PRECISION,
    high DOUBLE PRECISION,
    low DOUBLE PRECISION,
    close DOUBLE PRECISION NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_vix_date ON cboe_vix_history(date);

COMMENT ON TABLE cboe_vix_history IS 'CBOE VIX historical OHLC data';


-- ============================================================================
-- ICI ETF Weekly Flows
-- ============================================================================
CREATE TABLE IF NOT EXISTS ici_etf_weekly_flows (
    id SERIAL PRIMARY KEY,
    week_ending DATE NOT NULL,
    total_net_flows DOUBLE PRECISION,
    equity_net_flows DOUBLE PRECISION,
    hybrid_net_flows DOUBLE PRECISION,
    bond_net_flows DOUBLE PRECISION,
    commodity_net_flows DOUBLE PRECISION,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(week_ending)
);

CREATE INDEX IF NOT EXISTS idx_ici_week ON ici_etf_weekly_flows(week_ending);

COMMENT ON TABLE ici_etf_weekly_flows IS 'Investment Company Institute ETF weekly flow data';


-- ============================================================================
-- ICI ETF Monthly Flows
-- ============================================================================
CREATE TABLE IF NOT EXISTS ici_etf_monthly_flows (
    id SERIAL PRIMARY KEY,
    month_ending DATE NOT NULL,
    total_net_flows DOUBLE PRECISION,
    equity_net_flows DOUBLE PRECISION,
    hybrid_net_flows DOUBLE PRECISION,
    bond_net_flows DOUBLE PRECISION,
    commodity_net_flows DOUBLE PRECISION,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(month_ending)
);

CREATE INDEX IF NOT EXISTS idx_ici_month ON ici_etf_monthly_flows(month_ending);

COMMENT ON TABLE ici_etf_monthly_flows IS 'Investment Company Institute ETF monthly flow data';


-- ============================================================================
-- News Sentiment Data
-- ============================================================================
CREATE TABLE IF NOT EXISTS news_sentiment (
    id SERIAL PRIMARY KEY,
    source VARCHAR(100) NOT NULL,
    title TEXT NOT NULL,
    url TEXT,
    published_at TIMESTAMP,
    sentiment_score DOUBLE PRECISION,
    sentiment_label VARCHAR(20),
    relevance_score DOUBLE PRECISION,
    entities TEXT[],
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_news_published ON news_sentiment(published_at);
CREATE INDEX IF NOT EXISTS idx_news_sentiment ON news_sentiment(sentiment_label);
CREATE INDEX IF NOT EXISTS idx_news_source ON news_sentiment(source);

COMMENT ON TABLE news_sentiment IS 'News articles with sentiment analysis';


-- ============================================================================
-- Data Refresh Log
-- ============================================================================
CREATE TABLE IF NOT EXISTS data_refresh_log (
    id SERIAL PRIMARY KEY,
    data_type VARCHAR(50) NOT NULL,
    refresh_time TIMESTAMP NOT NULL,
    status VARCHAR(20) NOT NULL,
    records_updated INTEGER,
    error_message TEXT,
    duration_seconds DOUBLE PRECISION,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_refresh_log_type_time ON data_refresh_log(data_type, refresh_time);
CREATE INDEX IF NOT EXISTS idx_refresh_log_status ON data_refresh_log(status);

COMMENT ON TABLE data_refresh_log IS 'Log of all data refresh operations';


-- ============================================================================
-- Technical Features
-- ============================================================================
CREATE TABLE IF NOT EXISTS technical_features (
    id SERIAL PRIMARY KEY,
    ticker VARCHAR(20) NOT NULL,
    date DATE NOT NULL,
    rsi_14 DOUBLE PRECISION,
    macd DOUBLE PRECISION,
    macd_signal DOUBLE PRECISION,
    bb_upper DOUBLE PRECISION,
    bb_middle DOUBLE PRECISION,
    bb_lower DOUBLE PRECISION,
    sma_50 DOUBLE PRECISION,
    sma_200 DOUBLE PRECISION,
    ema_12 DOUBLE PRECISION,
    ema_26 DOUBLE PRECISION,
    atr_14 DOUBLE PRECISION,
    obv BIGINT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(ticker, date)
);

CREATE INDEX IF NOT EXISTS idx_technical_ticker_date ON technical_features(ticker, date);
CREATE INDEX IF NOT EXISTS idx_technical_date ON technical_features(date);

COMMENT ON TABLE technical_features IS 'Technical analysis indicators';


-- ============================================================================
-- Options Data
-- ============================================================================
CREATE TABLE IF NOT EXISTS options_data (
    id SERIAL PRIMARY KEY,
    ticker VARCHAR(20) NOT NULL,
    date DATE NOT NULL,
    put_volume BIGINT,
    call_volume BIGINT,
    put_call_ratio DOUBLE PRECISION,
    implied_volatility DOUBLE PRECISION,
    open_interest BIGINT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(ticker, date)
);

CREATE INDEX IF NOT EXISTS idx_options_ticker_date ON options_data(ticker, date);
CREATE INDEX IF NOT EXISTS idx_options_date ON options_data(date);

COMMENT ON TABLE options_data IS 'Options market data';


-- ============================================================================
-- ML Predictions
-- ============================================================================
CREATE TABLE IF NOT EXISTS ml_predictions (
    id SERIAL PRIMARY KEY,
    model_name VARCHAR(100) NOT NULL,
    ticker VARCHAR(20) NOT NULL,
    prediction_date DATE NOT NULL,
    target_date DATE NOT NULL,
    prediction_value DOUBLE PRECISION NOT NULL,
    confidence DOUBLE PRECISION,
    model_version VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(model_name, ticker, prediction_date, target_date)
);

CREATE INDEX IF NOT EXISTS idx_predictions_model_ticker ON ml_predictions(model_name, ticker);
CREATE INDEX IF NOT EXISTS idx_predictions_dates ON ml_predictions(prediction_date, target_date);

COMMENT ON TABLE ml_predictions IS 'Machine learning model predictions';


-- ============================================================================
-- Model Performance Metrics
-- ============================================================================
CREATE TABLE IF NOT EXISTS model_performance (
    id SERIAL PRIMARY KEY,
    model_name VARCHAR(100) NOT NULL,
    evaluation_date DATE NOT NULL,
    metric_name VARCHAR(50) NOT NULL,
    metric_value DOUBLE PRECISION NOT NULL,
    dataset_type VARCHAR(20),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(model_name, evaluation_date, metric_name, dataset_type)
);

CREATE INDEX IF NOT EXISTS idx_performance_model ON model_performance(model_name);
CREATE INDEX IF NOT EXISTS idx_performance_date ON model_performance(evaluation_date);

COMMENT ON TABLE model_performance IS 'Model performance metrics over time';


-- ============================================================================
-- Trigger to update updated_at timestamps
-- ============================================================================
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Apply the trigger to all tables with updated_at column
CREATE TRIGGER update_fred_data_updated_at BEFORE UPDATE ON fred_data 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
    
CREATE TRIGGER update_yfinance_ohlcv_updated_at BEFORE UPDATE ON yfinance_ohlcv 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
    
CREATE TRIGGER update_cboe_vix_history_updated_at BEFORE UPDATE ON cboe_vix_history 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
    
CREATE TRIGGER update_ici_etf_weekly_flows_updated_at BEFORE UPDATE ON ici_etf_weekly_flows 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
    
CREATE TRIGGER update_ici_etf_monthly_flows_updated_at BEFORE UPDATE ON ici_etf_monthly_flows 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
    
CREATE TRIGGER update_news_sentiment_updated_at BEFORE UPDATE ON news_sentiment 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
    
CREATE TRIGGER update_technical_features_updated_at BEFORE UPDATE ON technical_features 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
    
CREATE TRIGGER update_options_data_updated_at BEFORE UPDATE ON options_data 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
