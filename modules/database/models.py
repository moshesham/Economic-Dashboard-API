"""
SQLAlchemy ORM Models for Database Tables

Enables Alembic autogenerate and provides type-safe query interfaces.
"""

from sqlalchemy import (
    Column, String, Integer, BigInteger, Float, Boolean, Date, DateTime, JSON, Text,
    PrimaryKeyConstraint, Index, ForeignKey, func, create_engine
)
from sqlalchemy.orm import declarative_base, relationship
from datetime import datetime

Base = declarative_base()


# =============================================================================
# Economic Data Tables
# =============================================================================

class FREDData(Base):
    """FRED economic data time series"""
    __tablename__ = 'fred_data'

    series_id = Column(String, nullable=False)
    date = Column(Date, nullable=False)
    value = Column(Float)
    created_at = Column(DateTime, default=func.now())

    __table_args__ = (
        PrimaryKeyConstraint('series_id', 'date'),
        Index('idx_fred_series', 'series_id'),
        Index('idx_fred_date', 'date'),
    )


class YFinanceOHLCV(Base):
    """Stock OHLCV data from Yahoo Finance"""
    __tablename__ = 'yfinance_ohlcv'

    ticker = Column(String, nullable=False)
    date = Column(Date, nullable=False)
    open = Column(Float)
    high = Column(Float)
    low = Column(Float)
    close = Column(Float)
    volume = Column(BigInteger)
    adj_close = Column(Float)
    created_at = Column(DateTime, default=func.now())

    __table_args__ = (
        PrimaryKeyConstraint('ticker', 'date'),
        Index('idx_yf_ticker', 'ticker'),
        Index('idx_yf_date', 'date'),
        Index('idx_yf_ticker_date', 'ticker', 'date'),
    )


class OptionsData(Base):
    """Options data with put/call metrics"""
    __tablename__ = 'options_data'

    ticker = Column(String, nullable=False)
    date = Column(Date, nullable=False)
    expiration_date = Column(Date, nullable=False)
    put_volume = Column(BigInteger)
    call_volume = Column(BigInteger)
    put_open_interest = Column(BigInteger)
    call_open_interest = Column(BigInteger)
    put_call_volume_ratio = Column(Float)
    put_call_oi_ratio = Column(Float)
    total_put_iv = Column(Float)
    total_call_iv = Column(Float)
    iv_rank = Column(Float)
    iv_percentile = Column(Float)
    skew = Column(Float)
    created_at = Column(DateTime, default=func.now())

    __table_args__ = (
        PrimaryKeyConstraint('ticker', 'date', 'expiration_date'),
        Index('idx_options_ticker', 'ticker'),
        Index('idx_options_date', 'date'),
    )


# =============================================================================
# ICI ETF Flow Tables
# =============================================================================

class ICIETFWeeklyFlows(Base):
    """ICI weekly ETF flow statistics"""
    __tablename__ = 'ici_etf_weekly_flows'

    week_ending = Column(Date, nullable=False)
    fund_type = Column(String, nullable=False)
    estimated_flows = Column(Float)
    total_net_assets = Column(Float)
    created_at = Column(DateTime, default=func.now())

    __table_args__ = (
        PrimaryKeyConstraint('week_ending', 'fund_type'),
        Index('idx_ici_week_end', 'week_ending'),
        Index('idx_ici_week_fund', 'fund_type'),
    )


class ICIETFFlows(Base):
    """ICI monthly ETF flow statistics"""
    __tablename__ = 'ici_etf_flows'

    date = Column(Date, nullable=False)
    fund_category = Column(String, nullable=False)
    net_new_cash_flow = Column(Float)
    net_issuance = Column(Float)
    redemptions = Column(Float)
    reinvested_dividends = Column(Float)
    total_net_assets = Column(Float)
    created_at = Column(DateTime, default=func.now())

    __table_args__ = (
        PrimaryKeyConstraint('date', 'fund_category'),
        Index('idx_ici_month_date', 'date'),
        Index('idx_ici_month_category', 'fund_category'),
    )


# =============================================================================
# Market Indicator Tables
# =============================================================================

class MarketIndicators(Base):
    """Market-level indicators"""
    __tablename__ = 'market_indicators'

    date = Column(Date, primary_key=True, nullable=False)
    vix = Column(Float)
    vix_3m = Column(Float)
    vvix = Column(Float)
    skew = Column(Float)
    put_call_ratio = Column(Float)
    high_yield_spread = Column(Float)
    term_spread = Column(Float)
    credit_spread = Column(Float)
    created_at = Column(DateTime, default=func.now())

    __table_args__ = (
        Index('idx_market_date', 'date'),
    )


class CBOEVIXHistory(Base):
    """CBOE VIX OHLC history"""
    __tablename__ = 'cboe_vix_history'

    date = Column(Date, primary_key=True, nullable=False)
    open = Column(Float)
    high = Column(Float)
    low = Column(Float)
    close = Column(Float)
    created_at = Column(DateTime, default=func.now())

    __table_args__ = (
        Index('idx_cboe_vix_date', 'date'),
    )


class CBOEVIXTermStructure(Base):
    """CBOE VIX futures term structure"""
    __tablename__ = 'cboe_vix_term_structure'

    date = Column(Date, nullable=False)
    days_to_expiration = Column(Integer, nullable=False)
    expiration_date = Column(Date)
    contract_symbol = Column(String)
    settlement = Column(Float)
    vix_index = Column(Float)
    basis = Column(Float)
    created_at = Column(DateTime, default=func.now())

    __table_args__ = (
        PrimaryKeyConstraint('date', 'days_to_expiration'),
        Index('idx_cboe_vix_term_date', 'date'),
        Index('idx_cboe_vix_term_expiration', 'expiration_date'),
    )


# =============================================================================
# Technical Analysis Tables
# =============================================================================

class TechnicalFeatures(Base):
    """Technical analysis features per ticker/date"""
    __tablename__ = 'technical_features'

    ticker = Column(String, nullable=False)
    date = Column(Date, nullable=False)
    # Momentum
    rsi_14 = Column(Float)
    rsi_28 = Column(Float)
    stoch_k = Column(Float)
    stoch_d = Column(Float)
    williams_r = Column(Float)
    roc_10 = Column(Float)
    roc_20 = Column(Float)
    # Trend
    sma_20 = Column(Float)
    sma_50 = Column(Float)
    sma_200 = Column(Float)
    ema_12 = Column(Float)
    ema_26 = Column(Float)
    macd = Column(Float)
    macd_signal = Column(Float)
    macd_histogram = Column(Float)
    adx = Column(Float)
    # Volatility
    bb_upper = Column(Float)
    bb_middle = Column(Float)
    bb_lower = Column(Float)
    bb_width = Column(Float)
    atr_14 = Column(Float)
    keltner_upper = Column(Float)
    keltner_lower = Column(Float)
    # Volume
    obv = Column(Float)
    obv_sma = Column(Float)
    mfi = Column(Float)
    ad_line = Column(Float)
    cmf = Column(Float)
    vwap = Column(Float)
    # Custom
    price_to_sma20 = Column(Float)
    price_to_sma50 = Column(Float)
    price_to_sma200 = Column(Float)
    volume_ratio = Column(Float)
    created_at = Column(DateTime, default=func.now())

    __table_args__ = (
        PrimaryKeyConstraint('ticker', 'date'),
        Index('idx_tech_ticker', 'ticker'),
        Index('idx_tech_date', 'date'),
        Index('idx_tech_ticker_date', 'ticker', 'date'),  # New composite index
    )


class DerivedFeatures(Base):
    """Derived/engineered features per ticker/date"""
    __tablename__ = 'derived_features'

    ticker = Column(String, nullable=False)
    date = Column(Date, nullable=False)
    # Feature interactions
    rsi_macd_interaction = Column(Float)
    volume_price_divergence = Column(Float)
    momentum_volatility_ratio = Column(Float)
    # Regime detection
    volatility_regime = Column(String)
    trend_regime = Column(String)
    volume_regime = Column(String)
    # Z-scores
    price_zscore = Column(Float)
    volume_zscore = Column(Float)
    rsi_zscore = Column(Float)
    # Cross-asset
    sp500_correlation_30d = Column(Float)
    sector_relative_strength = Column(Float)
    market_beta = Column(Float)
    # Time-based
    day_of_week = Column(Integer)
    week_of_month = Column(Integer)
    month = Column(Integer)
    quarter = Column(Integer)
    # Sentiment proxies
    high_low_range = Column(Float)
    close_position_in_range = Column(Float)
    gap_percentage = Column(Float)
    created_at = Column(DateTime, default=func.now())

    __table_args__ = (
        PrimaryKeyConstraint('ticker', 'date'),
        Index('idx_derived_ticker', 'ticker'),
        Index('idx_derived_date', 'date'),
    )


# =============================================================================
# ML Pipeline Tables
# =============================================================================

class MLTrainingData(Base):
    """ML training dataset records"""
    __tablename__ = 'ml_training_data'

    ticker = Column(String, nullable=False)
    as_of_date = Column(Date, nullable=False)
    target_date = Column(Date, nullable=False)
    target_direction = Column(Boolean)
    target_return = Column(Float)
    split_type = Column(String)  # 'train', 'validation', 'test'
    fold_id = Column(Integer)
    created_at = Column(DateTime, default=func.now())

    __table_args__ = (
        PrimaryKeyConstraint('ticker', 'as_of_date'),
        Index('idx_ml_train_ticker', 'ticker'),
        Index('idx_ml_train_split', 'split_type'),
    )


class MLPredictions(Base):
    """ML model predictions"""
    __tablename__ = 'ml_predictions'

    ticker = Column(String, nullable=False)
    prediction_date = Column(Date, nullable=False)
    target_date = Column(Date, nullable=False)
    model_version = Column(String, nullable=False)
    predicted_direction = Column(Boolean)
    predicted_probability = Column(Float)
    xgboost_prob = Column(Float)
    lightgbm_prob = Column(Float)
    lstm_prob = Column(Float)
    ensemble_prob = Column(Float)
    confidence_score = Column(Float)
    top_features = Column(JSON)
    created_at = Column(DateTime, default=func.now())

    __table_args__ = (
        PrimaryKeyConstraint('ticker', 'prediction_date', 'model_version'),
        Index('idx_ml_pred_ticker', 'ticker'),
        Index('idx_ml_pred_date', 'prediction_date'),
        Index('idx_ml_pred_target', 'target_date'),
        Index('idx_ml_pred_ticker_date', 'ticker', 'prediction_date'),  # New composite
    )


class ModelPerformance(Base):
    """Model performance tracking"""
    __tablename__ = 'model_performance'

    model_version = Column(String, nullable=False)
    evaluation_date = Column(Date, nullable=False)
    ticker = Column(String, nullable=False)
    accuracy = Column(Float)
    precision = Column(Float)
    recall = Column(Float)
    f1_score = Column(Float)
    auc_roc = Column(Float)
    log_loss = Column(Float)
    brier_score = Column(Float)
    sharpe_ratio = Column(Float)
    total_predictions = Column(Integer)
    correct_predictions = Column(Integer)
    evaluation_period_days = Column(Integer)
    created_at = Column(DateTime, default=func.now())

    __table_args__ = (
        PrimaryKeyConstraint('model_version', 'evaluation_date', 'ticker'),
        Index('idx_perf_model', 'model_version'),
        Index('idx_perf_date', 'evaluation_date'),
    )


class ModelRegistry(Base):
    """Model registry for versioned model artifacts"""
    __tablename__ = 'model_registry'

    model_id = Column(String, primary_key=True, nullable=False)
    model_name = Column(String, nullable=False)
    model_version = Column(String, nullable=False)
    model_type = Column(String)  # 'xgboost', 'lightgbm', 'ensemble'
    ticker = Column(String)
    artifact_path = Column(String)
    feature_names = Column(JSON)
    hyperparameters = Column(JSON)
    training_metrics = Column(JSON)
    validation_metrics = Column(JSON)
    status = Column(String, default='staging')  # 'staging', 'production', 'archived'
    trained_at = Column(DateTime)
    promoted_at = Column(DateTime)
    created_at = Column(DateTime, default=func.now())

    __table_args__ = (
        Index('idx_registry_name_version', 'model_name', 'model_version'),
        Index('idx_registry_status', 'status'),
        Index('idx_registry_ticker', 'ticker'),
    )


# =============================================================================
# Ops / Monitoring Tables
# =============================================================================

class DataRefreshLog(Base):
    """Data refresh operation log"""
    __tablename__ = 'data_refresh_log'

    refresh_id = Column(Integer, primary_key=True, autoincrement=True)
    data_source = Column(String, nullable=False)
    refresh_start = Column(DateTime, nullable=False)
    refresh_end = Column(DateTime)
    status = Column(String)  # 'running', 'completed', 'failed'
    records_processed = Column(Integer)
    error_message = Column(String)
    created_at = Column(DateTime, default=func.now())

    __table_args__ = (
        Index('idx_refresh_source', 'data_source'),
        Index('idx_refresh_status', 'status'),
    )


class DataRetentionPolicy(Base):
    """Data retention policy definitions"""
    __tablename__ = 'data_retention_policy'

    table_name = Column(String, primary_key=True, nullable=False)
    retention_days = Column(Integer, nullable=False)
    archive_to_parquet = Column(Boolean, default=True)
    partition_column = Column(String)
    description = Column(String)
    last_cleanup = Column(DateTime)
    created_at = Column(DateTime, default=func.now())


class FeatureDrift(Base):
    """Feature drift monitoring"""
    __tablename__ = 'feature_drift'

    feature_name = Column(String, nullable=False)
    analysis_date = Column(Date, nullable=False)
    reference_start_date = Column(Date)
    reference_end_date = Column(Date)
    current_start_date = Column(Date)
    current_end_date = Column(Date)
    ks_statistic = Column(Float)
    psi_value = Column(Float)
    drift_detected = Column(Boolean)
    drift_severity = Column(String)  # 'none', 'low', 'medium', 'high'
    created_at = Column(DateTime, default=func.now())

    __table_args__ = (
        PrimaryKeyConstraint('feature_name', 'analysis_date'),
        Index('idx_drift_feature', 'feature_name'),
        Index('idx_drift_date', 'analysis_date'),
    )


# =============================================================================
# Sentiment / News Tables
# =============================================================================

class NewsSentiment(Base):
    """News sentiment data"""
    __tablename__ = 'news_sentiment'

    id = Column(Integer, primary_key=True, autoincrement=True)
    ticker = Column(String)
    headline = Column(Text)
    source = Column(String)
    published_at = Column(DateTime)
    sentiment_score = Column(Float)
    sentiment_label = Column(String)  # 'positive', 'negative', 'neutral'
    relevance_score = Column(Float)
    url = Column(String)
    created_at = Column(DateTime, default=func.now())

    __table_args__ = (
        Index('idx_news_ticker', 'ticker'),
        Index('idx_news_published', 'published_at'),
        Index('idx_news_sentiment', 'sentiment_label'),
    )


# =============================================================================
# SEC Data Tables
# =============================================================================

class SECSubmissions(Base):
    """SEC filing submissions metadata"""
    __tablename__ = 'sec_submissions'

    adsh = Column(String, primary_key=True, nullable=False)
    cik = Column(BigInteger, nullable=False)
    name = Column(String)
    sic = Column(BigInteger)
    countryba = Column(String)
    stprba = Column(String)
    cityba = Column(String)
    zipba = Column(String)
    bas1 = Column(String)
    bas2 = Column(String)
    baph = Column(String)
    countryma = Column(String)
    stprma = Column(String)
    cityma = Column(String)
    zipma = Column(String)
    mas1 = Column(String)
    mas2 = Column(String)
    countryinc = Column(String)
    stprinc = Column(String)
    ein = Column(BigInteger)
    former = Column(String)
    changed = Column(String)
    accession = Column(String)
    form = Column(String)
    period = Column(Date)
    fy = Column(Integer)
    fp = Column(String)
    filed = Column(Date)
    accepted = Column(DateTime)
    preaccession = Column(String)
    instance = Column(String)
    nciks = Column(Integer)
    aciks = Column(String)
    data_year = Column(Integer)
    data_quarter = Column(Integer)
    created_at = Column(DateTime, default=func.now())

    __table_args__ = (
        Index('idx_sec_sub_cik', 'cik'),
        Index('idx_sec_sub_form', 'form'),
        Index('idx_sec_sub_filed', 'filed'),
        Index('idx_sec_sub_period', 'period'),
    )


class SECFinancialStatements(Base):
    """SEC financial statement numeric data"""
    __tablename__ = 'sec_financial_statements'

    adsh = Column(String, nullable=False)
    tag = Column(String, nullable=False)
    version = Column(String)
    coreg = Column(String, nullable=False, default='')
    ddate = Column(Date, nullable=False)
    qtrs = Column(Integer, nullable=False)
    uom = Column(String)
    value = Column(Float)
    footnote = Column(String)
    data_year = Column(Integer)
    data_quarter = Column(Integer)
    created_at = Column(DateTime, default=func.now())

    __table_args__ = (
        PrimaryKeyConstraint('adsh', 'tag', 'ddate', 'qtrs', 'coreg'),
        Index('idx_sec_fs_adsh', 'adsh'),
        Index('idx_sec_fs_tag', 'tag'),
        Index('idx_sec_fs_ddate', 'ddate'),
    )


class SECCompanyFacts(Base):
    """SEC company facts (XBRL data)"""
    __tablename__ = 'sec_company_facts'

    cik = Column(String, nullable=False)
    concept = Column(String, nullable=False)
    unit = Column(String, nullable=False, default='USD')
    value = Column(Float)
    start_date = Column(Date)
    end_date = Column(Date, nullable=False)
    fy = Column(Integer)
    fp = Column(String)
    form = Column(String)
    filed = Column(Date)
    accn = Column(String)
    created_at = Column(DateTime, default=func.now())

    __table_args__ = (
        PrimaryKeyConstraint('cik', 'concept', 'end_date', 'unit'),
        Index('idx_sec_facts_cik', 'cik'),
        Index('idx_sec_facts_concept', 'concept'),
        Index('idx_sec_facts_end_date', 'end_date'),
    )


# =============================================================================
# SEC Additional Tables
# =============================================================================

class SECFilings(Base):
    """SEC filings data"""
    __tablename__ = 'sec_filings'

    cik = Column(String, nullable=False)
    filing_date = Column(Date, nullable=False)
    form_type = Column(String)
    accession_number = Column(String)
    file_number = Column(String)
    film_number = Column(String)
    created_at = Column(DateTime, default=func.now())

    __table_args__ = (
        PrimaryKeyConstraint('cik', 'filing_date', 'accession_number'),
        Index('idx_sec_filings_cik', 'cik'),
        Index('idx_sec_filings_date', 'filing_date'),
        Index('idx_sec_filings_form', 'form_type'),
    )


class SECFailsToDeliver(Base):
    """SEC fails to deliver data"""
    __tablename__ = 'sec_fails_to_deliver'

    cusip = Column(String, nullable=False)
    settlement_date = Column(Date, nullable=False)
    symbol = Column(String)
    quantity = Column(BigInteger)
    description = Column(String)
    price = Column(Float)
    created_at = Column(DateTime, default=func.now())

    __table_args__ = (
        PrimaryKeyConstraint('cusip', 'settlement_date'),
        Index('idx_sec_ftd_cusip', 'cusip'),
        Index('idx_sec_ftd_date', 'settlement_date'),
        Index('idx_sec_ftd_symbol', 'symbol'),
    )


class SEC13FHoldings(Base):
    """SEC 13F holdings data"""
    __tablename__ = 'sec_13f_holdings'

    cik = Column(String, nullable=False)
    filing_date = Column(Date, nullable=False)
    cusip = Column(String, nullable=False)
    security_name = Column(String)
    shares = Column(BigInteger)
    market_value = Column(BigInteger)
    put_call = Column(String)
    investment_discretion = Column(String)
    voting_authority_sole = Column(BigInteger)
    voting_authority_shared = Column(BigInteger)
    voting_authority_none = Column(BigInteger)
    created_at = Column(DateTime, default=func.now())

    __table_args__ = (
        PrimaryKeyConstraint('cik', 'filing_date', 'cusip'),
        Index('idx_sec_13f_cik', 'cik'),
        Index('idx_sec_13f_filing_date', 'filing_date'),
        Index('idx_sec_13f_cusip', 'cusip'),
    )


# =============================================================================
# Margin Call Risk Tables
# =============================================================================

class LeverageMetrics(Base):
    """Leverage and margin metrics"""
    __tablename__ = 'leverage_metrics'

    ticker = Column(String, nullable=False)
    date = Column(Date, nullable=False)
    short_interest = Column(BigInteger)
    short_interest_ratio = Column(Float)
    days_to_cover = Column(Float)
    short_percent_float = Column(Float)
    shares_outstanding = Column(BigInteger)
    float_shares = Column(BigInteger)
    avg_volume_10d = Column(BigInteger)
    created_at = Column(DateTime, default=func.now())

    __table_args__ = (
        PrimaryKeyConstraint('ticker', 'date'),
        Index('idx_leverage_ticker', 'ticker'),
        Index('idx_leverage_date', 'date'),
    )


class VIXTermStructure(Base):
    """VIX and volatility term structure"""
    __tablename__ = 'vix_term_structure'

    date = Column(Date, primary_key=True, nullable=False)
    vix = Column(Float)
    vix_3m = Column(Float)
    vix_6m = Column(Float)
    vvix = Column(Float)
    vix_term_spread = Column(Float)
    vix_regime = Column(String)
    backwardation_ratio = Column(Float)
    stress_score = Column(Float)
    created_at = Column(DateTime, default=func.now())

    __table_args__ = (
        Index('idx_vix_date', 'date'),
        Index('idx_vix_regime', 'vix_regime'),
    )


class LeveragedETFData(Base):
    """Leveraged ETF tracking"""
    __tablename__ = 'leveraged_etf_data'

    ticker = Column(String, nullable=False)
    date = Column(Date, nullable=False)
    close = Column(Float)
    volume = Column(BigInteger)
    volume_ratio = Column(Float)
    intraday_volatility = Column(Float)
    tracking_error = Column(Float)
    premium_discount = Column(Float)
    stress_indicator = Column(Float)
    created_at = Column(DateTime, default=func.now())

    __table_args__ = (
        PrimaryKeyConstraint('ticker', 'date'),
        Index('idx_lev_etf_ticker', 'ticker'),
        Index('idx_lev_etf_date', 'date'),
    )


class MarginCallRisk(Base):
    """Composite margin call risk scores"""
    __tablename__ = 'margin_call_risk'

    ticker = Column(String, nullable=False)
    date = Column(Date, nullable=False)
    leverage_score = Column(Float)
    volatility_score = Column(Float)
    options_score = Column(Float)
    liquidity_score = Column(Float)
    composite_risk_score = Column(Float)
    risk_level = Column(String)
    vix_regime = Column(String)
    short_interest_pct = Column(Float)
    put_call_ratio = Column(Float)
    iv_rank = Column(Float)
    created_at = Column(DateTime, default=func.now())

    __table_args__ = (
        PrimaryKeyConstraint('ticker', 'date'),
        Index('idx_margin_risk_ticker', 'ticker'),
        Index('idx_margin_risk_date', 'date'),
        Index('idx_margin_risk_level', 'risk_level'),
        Index('idx_margin_composite', 'composite_risk_score'),
    )


# =============================================================================
# Sentiment Tables (Additional)
# =============================================================================

class SentimentSummary(Base):
    """Aggregated sentiment summaries"""
    __tablename__ = 'sentiment_summary'

    ticker = Column(String, nullable=False)
    analysis_date = Column(Date, nullable=False)
    article_count = Column(Integer)
    avg_sentiment = Column(Float)
    median_sentiment = Column(Float)
    positive_count = Column(Integer)
    negative_count = Column(Integer)
    neutral_count = Column(Integer)
    sentiment_trend = Column(String)  # 'bullish', 'slightly_bullish', 'neutral', 'slightly_bearish', 'bearish'
    momentum = Column(Float)
    confidence = Column(Float)
    recommendation = Column(String)
    created_at = Column(DateTime, default=func.now())

    __table_args__ = (
        PrimaryKeyConstraint('ticker', 'analysis_date'),
        Index('idx_summary_ticker', 'ticker'),
        Index('idx_summary_date', 'analysis_date'),
    )


class GoogleTrends(Base):
    """Google Trends data"""
    __tablename__ = 'google_trends'

    keyword = Column(String, nullable=False)
    date = Column(Date, nullable=False)
    interest_value = Column(Float)
    geo = Column(String, default='US')
    created_at = Column(DateTime, default=func.now())

    __table_args__ = (
        PrimaryKeyConstraint('keyword', 'date', 'geo'),
        Index('idx_trends_keyword', 'keyword'),
        Index('idx_trends_date', 'date'),
    )


# =============================================================================
# Financial Health & Sector Tables
# =============================================================================

class FinancialHealthScores(Base):
    """Financial health scores for companies"""
    __tablename__ = 'financial_health_scores'

    ticker = Column(String, nullable=False)
    analysis_date = Column(Date, nullable=False)
    liquidity_score = Column(Float)
    profitability_score = Column(Float)
    leverage_score = Column(Float)
    efficiency_score = Column(Float)
    growth_score = Column(Float)
    composite_score = Column(Float)
    health_grade = Column(String)  # 'A', 'B', 'C', 'D', 'F'
    bankruptcy_risk = Column(Float)
    created_at = Column(DateTime, default=func.now())

    __table_args__ = (
        PrimaryKeyConstraint('ticker', 'analysis_date'),
        Index('idx_health_ticker', 'ticker'),
        Index('idx_health_date', 'analysis_date'),
        Index('idx_health_grade', 'health_grade'),
    )


class SectorRotationAnalysis(Base):
    """Sector rotation analysis"""
    __tablename__ = 'sector_rotation_analysis'

    sector = Column(String, nullable=False)
    analysis_date = Column(Date, nullable=False)
    momentum_score = Column(Float)
    relative_strength = Column(Float)
    volume_trend = Column(Float)
    breadth_indicator = Column(Float)
    rotation_phase = Column(String)  # 'leading', 'weakening', 'lagging', 'improving'
    recommendation = Column(String)  # 'overweight', 'neutral', 'underweight'
    created_at = Column(DateTime, default=func.now())

    __table_args__ = (
        PrimaryKeyConstraint('sector', 'analysis_date'),
        Index('idx_sector_rotation_sector', 'sector'),
        Index('idx_sector_rotation_date', 'analysis_date'),
        Index('idx_sector_rotation_phase', 'rotation_phase'),
    )


class SectorRelativeStrength(Base):
    """Sector relative strength tracking"""
    __tablename__ = 'sector_relative_strength'

    sector = Column(String, nullable=False)
    date = Column(Date, nullable=False)
    price_return_1w = Column(Float)
    price_return_1m = Column(Float)
    price_return_3m = Column(Float)
    price_return_6m = Column(Float)
    rs_score = Column(Float)  # Relative strength score
    rs_rank = Column(Integer)  # Rank among sectors
    breadth_ratio = Column(Float)  # % stocks above 200-day MA
    volume_surge = Column(Float)  # Volume vs average
    created_at = Column(DateTime, default=func.now())

    __table_args__ = (
        PrimaryKeyConstraint('sector', 'date'),
        Index('idx_sector_strength_sector', 'sector'),
        Index('idx_sector_strength_date', 'date'),
        Index('idx_sector_strength_rank', 'rs_rank'),
    )


# =============================================================================
# API Keys Table
# =============================================================================

class APIKey(Base):
    """API key management"""
    __tablename__ = 'api_keys'

    key_id = Column(String, primary_key=True, nullable=False)
    key_hash = Column(String, nullable=False)
    name = Column(String, nullable=False)
    owner = Column(String)
    scopes = Column(JSON)  # e.g., ['read', 'write', 'admin']
    rate_limit = Column(Integer, default=100)  # requests per minute
    is_active = Column(Boolean, default=True)
    expires_at = Column(DateTime)
    last_used_at = Column(DateTime)
    created_at = Column(DateTime, default=func.now())

    __table_args__ = (
        Index('idx_api_key_hash', 'key_hash'),
        Index('idx_api_key_active', 'is_active'),
    )


# =============================================================================
# Open Data Sources Tables
# =============================================================================

class WorldBankIndicators(Base):
    """World Bank economic indicators"""
    __tablename__ = 'worldbank_indicators'

    country_code = Column(String, nullable=False)
    country_name = Column(String)
    indicator_code = Column(String, nullable=False)
    indicator_name = Column(String)
    year = Column(Integer, nullable=False)
    date = Column(Date, nullable=False)
    value = Column(Float)
    unit = Column(String)
    decimal = Column(Integer)
    created_at = Column(DateTime, default=func.now())

    __table_args__ = (
        PrimaryKeyConstraint('country_code', 'indicator_code', 'year'),
        Index('idx_wb_country', 'country_code'),
        Index('idx_wb_indicator', 'indicator_code'),
        Index('idx_wb_date', 'date'),
    )


class IMFExchangeRates(Base):
    """IMF exchange rate data"""
    __tablename__ = 'imf_exchange_rates'

    country_code = Column(String, nullable=False)
    year = Column(Integer, nullable=False)
    date = Column(Date, nullable=False)
    exchange_rate = Column(Float)
    indicator = Column(String)
    indicator_name = Column(String)
    created_at = Column(DateTime, default=func.now())

    __table_args__ = (
        PrimaryKeyConstraint('country_code', 'year'),
        Index('idx_imf_xr_country', 'country_code'),
        Index('idx_imf_xr_date', 'date'),
    )


class IMFIndicators(Base):
    """IMF economic indicators"""
    __tablename__ = 'imf_indicators'

    country_code = Column(String, nullable=False)
    indicator = Column(String, nullable=False)
    year = Column(Integer, nullable=False)
    date = Column(Date, nullable=False)
    value = Column(Float)
    created_at = Column(DateTime, default=func.now())

    __table_args__ = (
        PrimaryKeyConstraint('country_code', 'indicator', 'year'),
        Index('idx_imf_ind_country', 'country_code'),
        Index('idx_imf_ind_indicator', 'indicator'),
        Index('idx_imf_ind_date', 'date'),
    )


class OECDIndicators(Base):
    """OECD economic indicators"""
    __tablename__ = 'oecd_indicators'

    country_code = Column(String, nullable=False)
    indicator = Column(String, nullable=False)
    indicator_name = Column(String)
    date = Column(Date, nullable=False)
    period = Column(String)
    year = Column(Integer)
    value = Column(Float)
    created_at = Column(DateTime, default=func.now())

    __table_args__ = (
        PrimaryKeyConstraint('country_code', 'indicator', 'date'),
        Index('idx_oecd_country', 'country_code'),
        Index('idx_oecd_indicator', 'indicator'),
        Index('idx_oecd_date', 'date'),
    )


class BLSData(Base):
    """Bureau of Labor Statistics data"""
    __tablename__ = 'bls_data'

    series_id = Column(String, nullable=False)
    series_name = Column(String)
    year = Column(Integer, nullable=False)
    period = Column(String, nullable=False)
    date = Column(Date, nullable=False)
    value = Column(Float)
    created_at = Column(DateTime, default=func.now())

    __table_args__ = (
        PrimaryKeyConstraint('series_id', 'year', 'period'),
        Index('idx_bls_series', 'series_id'),
        Index('idx_bls_date', 'date'),
    )


class CensusData(Base):
    """US Census Bureau economic data"""
    __tablename__ = 'census_data'

    date = Column(Date, nullable=False)
    indicator = Column(String, nullable=False)
    category = Column(String)
    value = Column(Float)
    seasonally_adjusted = Column(Boolean, default=False)
    created_at = Column(DateTime, default=func.now())

    __table_args__ = (
        PrimaryKeyConstraint('date', 'indicator', 'category'),
        Index('idx_census_date', 'date'),
        Index('idx_census_indicator', 'indicator'),
    )


class EIAData(Base):
    """Energy Information Administration data"""
    __tablename__ = 'eia_data'

    series_id = Column(String, nullable=False)
    series_name = Column(String)
    period = Column(String, nullable=False)
    date = Column(Date, nullable=False)
    value = Column(Float)
    created_at = Column(DateTime, default=func.now())

    __table_args__ = (
        PrimaryKeyConstraint('series_id', 'period'),
        Index('idx_eia_series', 'series_id'),
        Index('idx_eia_date', 'date'),
    )
