"""
Pydantic schemas for feature endpoints.
"""

from datetime import datetime
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field

from api.v1.schemas.common import TimestampMixin


# ============================================================================
# Technical Features
# ============================================================================

class MovingAverages(BaseModel):
    """Moving average indicators."""
    ma_5: Optional[float] = Field(None, description="5-day MA")
    ma_10: Optional[float] = Field(None, description="10-day MA")
    ma_20: Optional[float] = Field(None, description="20-day MA")
    ma_50: Optional[float] = Field(None, description="50-day MA")
    ma_200: Optional[float] = Field(None, description="200-day MA")
    ema_12: Optional[float] = Field(None, description="12-day EMA")
    ema_26: Optional[float] = Field(None, description="26-day EMA")
    price_to_ma_20: Optional[float] = Field(None, description="Price relative to 20-day MA")
    price_to_ma_50: Optional[float] = Field(None, description="Price relative to 50-day MA")
    price_to_ma_200: Optional[float] = Field(None, description="Price relative to 200-day MA")


class MomentumIndicators(BaseModel):
    """Momentum indicators."""
    rsi_14: Optional[float] = Field(None, ge=0, le=100, description="14-day RSI")
    macd: Optional[float] = Field(None, description="MACD line")
    macd_signal: Optional[float] = Field(None, description="MACD signal line")
    macd_histogram: Optional[float] = Field(None, description="MACD histogram")
    stochastic_k: Optional[float] = Field(None, description="Stochastic %K")
    stochastic_d: Optional[float] = Field(None, description="Stochastic %D")
    williams_r: Optional[float] = Field(None, description="Williams %R")
    cci: Optional[float] = Field(None, description="Commodity Channel Index")


class VolatilityIndicators(BaseModel):
    """Volatility indicators."""
    volatility_5d: Optional[float] = Field(None, description="5-day annualized volatility")
    volatility_20d: Optional[float] = Field(None, description="20-day annualized volatility")
    volatility_60d: Optional[float] = Field(None, description="60-day annualized volatility")
    atr_14: Optional[float] = Field(None, description="14-day Average True Range")
    atr_percent: Optional[float] = Field(None, description="ATR as % of price")
    bb_upper: Optional[float] = Field(None, description="Bollinger Band upper")
    bb_lower: Optional[float] = Field(None, description="Bollinger Band lower")
    bb_width: Optional[float] = Field(None, description="Bollinger Band width")
    bb_position: Optional[float] = Field(None, description="Position within Bollinger Bands")


class VolumeIndicators(BaseModel):
    """Volume indicators."""
    avg_volume_20d: Optional[float] = Field(None, description="20-day average volume")
    volume_ratio: Optional[float] = Field(None, description="Current volume / avg volume")
    obv: Optional[float] = Field(None, description="On-Balance Volume")
    vwap: Optional[float] = Field(None, description="Volume Weighted Average Price")
    accumulation_distribution: Optional[float] = Field(None, description="A/D line")


class PriceReturns(BaseModel):
    """Price return metrics."""
    return_1d: Optional[float] = Field(None, description="1-day return")
    return_5d: Optional[float] = Field(None, description="5-day return")
    return_20d: Optional[float] = Field(None, description="20-day return")
    return_60d: Optional[float] = Field(None, description="60-day return")
    return_252d: Optional[float] = Field(None, description="252-day (1 year) return")
    max_drawdown_20d: Optional[float] = Field(None, description="20-day max drawdown")


class TechnicalFeaturesResponse(TimestampMixin):
    """Response for technical features endpoint."""
    ticker: str
    price: float
    moving_averages: MovingAverages
    momentum: MomentumIndicators
    volatility: VolatilityIndicators
    volume: VolumeIndicators
    returns: PriceReturns
    trend_signal: str = Field(..., description="BULLISH, BEARISH, or NEUTRAL")


# ============================================================================
# Options-Derived Features
# ============================================================================

class ImpliedVolatilityMetrics(BaseModel):
    """Implied volatility metrics."""
    iv_atm: Optional[float] = Field(None, description="ATM implied volatility")
    iv_atm_calls: Optional[float] = Field(None, description="ATM call IV")
    iv_atm_puts: Optional[float] = Field(None, description="ATM put IV")
    iv_skew: Optional[float] = Field(None, description="IV skew (OTM puts - OTM calls)")
    iv_term_structure: Optional[Dict[str, float]] = Field(None, description="IV by expiration")
    iv_percentile: Optional[float] = Field(None, description="IV percentile rank")
    iv_vs_hv: Optional[float] = Field(None, description="IV / Historical Volatility ratio")


class OptionsFlowMetrics(BaseModel):
    """Options flow metrics."""
    put_call_ratio_volume: Optional[float] = Field(None, description="Put/Call volume ratio")
    put_call_ratio_oi: Optional[float] = Field(None, description="Put/Call open interest ratio")
    call_volume: Optional[int] = None
    put_volume: Optional[int] = None
    call_oi: Optional[int] = None
    put_oi: Optional[int] = None
    unusual_activity_score: Optional[float] = Field(None, description="Unusual activity detection")


class OptionsFeaturesResponse(TimestampMixin):
    """Response for options features endpoint."""
    ticker: str
    underlying_price: float
    implied_volatility: ImpliedVolatilityMetrics
    options_flow: OptionsFlowMetrics
    sentiment_signal: str = Field(..., description="Options-derived sentiment")


# ============================================================================
# Derived/Composite Features
# ============================================================================

class FinancialHealthMetrics(BaseModel):
    """Financial health metrics."""
    composite_score: Optional[float] = Field(None, ge=0, le=100)
    profitability_score: Optional[float] = None
    leverage_score: Optional[float] = None
    liquidity_score: Optional[float] = None
    efficiency_score: Optional[float] = None
    health_rating: Optional[str] = Field(None, description="A, B, C, D, F")


class MarginRiskMetrics(BaseModel):
    """Margin call risk metrics."""
    composite_score: Optional[float] = Field(None, ge=0, le=1)
    leverage_component: Optional[float] = None
    volatility_component: Optional[float] = None
    options_component: Optional[float] = None
    liquidity_component: Optional[float] = None
    risk_level: Optional[str] = Field(None, description="Low, Medium, High, Critical")


class SentimentMetrics(BaseModel):
    """Sentiment metrics."""
    news_sentiment: Optional[float] = Field(None, ge=-1, le=1)
    insider_sentiment: Optional[float] = Field(None, ge=-1, le=1)
    options_sentiment: Optional[float] = Field(None, ge=-1, le=1)
    social_sentiment: Optional[float] = Field(None, ge=-1, le=1)
    composite_sentiment: Optional[float] = Field(None, ge=-1, le=1)


class DerivedFeaturesResponse(TimestampMixin):
    """Response for derived features endpoint."""
    ticker: str
    financial_health: FinancialHealthMetrics
    margin_risk: MarginRiskMetrics
    sentiment: SentimentMetrics
    composite_signal: str


# ============================================================================
# All Features Combined
# ============================================================================

class AllFeaturesResponse(TimestampMixin):
    """Response for all features endpoint."""
    ticker: str
    price: float
    technical: TechnicalFeaturesResponse
    options: Optional[OptionsFeaturesResponse] = None
    derived: DerivedFeaturesResponse
    feature_count: int = Field(..., description="Total number of features")
    last_computed: datetime
