"""
Pydantic schemas for signals endpoints.
"""

from datetime import datetime
from typing import Optional, Dict, List, Any
from pydantic import BaseModel, Field

from api.v1.schemas.common import TimestampMixin, RiskLevel, SignalStrength


# ============================================================================
# Margin Risk Signals
# ============================================================================

class MarginRiskComponents(BaseModel):
    """Component scores for margin risk."""
    leverage: float = Field(..., ge=0, le=1, description="Leverage risk component")
    volatility: float = Field(..., ge=0, le=1, description="Volatility risk component")
    options: float = Field(..., ge=0, le=1, description="Options risk component")
    liquidity: float = Field(..., ge=0, le=1, description="Liquidity risk component")


class MarginRiskResponse(TimestampMixin):
    """Response for margin risk endpoint."""
    ticker: str
    composite_risk_score: float = Field(..., ge=0, le=1)
    risk_level: str = Field(..., description="Low, Medium, High, Critical")
    components: MarginRiskComponents
    signal: str = Field(..., description="SAFE, CAUTION, WARNING, DANGER")
    alerts: List[str] = Field(default_factory=list, description="Active risk alerts")
    
    @property
    def is_elevated(self) -> bool:
        return self.composite_risk_score >= 0.5


class MarginRiskListResponse(TimestampMixin):
    """Response for margin risk list endpoint."""
    signals: List[MarginRiskResponse]
    count: int
    threshold: float
    elevated_count: int = Field(..., description="Count with score >= threshold")


# ============================================================================
# Insider Signals
# ============================================================================

class InsiderSignalResponse(TimestampMixin):
    """Response for insider signal endpoint."""
    ticker: str
    sentiment_score: float = Field(..., ge=-1, le=1, description="Insider sentiment -1 to +1")
    signal: str = Field(..., description="BEARISH, NEUTRAL, BULLISH")
    net_shares: int = Field(..., description="Net shares bought/sold")
    net_value: float = Field(..., description="Net transaction value")
    transaction_count: int
    notable_transactions: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Notable insider transactions"
    )
    period_days: int
    cluster_buying: bool = Field(False, description="Multiple insiders buying")
    large_transaction_alert: bool = Field(False, description="Unusually large transaction")


# ============================================================================
# Sector Rotation Signals
# ============================================================================

class SectorPerformance(BaseModel):
    """Single sector performance metrics."""
    sector: str
    etf: str = Field(..., description="Sector ETF ticker")
    return_1w: float
    return_1m: float
    return_3m: float
    relative_strength: float = Field(..., description="Relative to SPY")
    momentum_score: float = Field(..., ge=-1, le=1)
    rank: int = Field(..., ge=1)


class SectorRotationResponse(TimestampMixin):
    """Response for sector rotation endpoint."""
    market_regime: str = Field(..., description="Risk-On, Risk-Off")
    sector_rankings: List[SectorPerformance]
    leading_sectors: List[str] = Field(..., description="Top performing sectors")
    lagging_sectors: List[str] = Field(..., description="Bottom performing sectors")
    rotation_signal: str = Field(..., description="Current rotation recommendation")
    regime_strength: float = Field(..., ge=0, le=1)


# ============================================================================
# Combined Signals Dashboard
# ============================================================================

class PredictionSignal(BaseModel):
    """ML prediction signal component."""
    direction: str
    confidence: float


class MarginRiskSignal(BaseModel):
    """Margin risk signal component."""
    score: float
    level: str


class FinancialHealthSignal(BaseModel):
    """Financial health signal component."""
    score: float
    rating: str


class OverallSignal(BaseModel):
    """Overall composite signal."""
    score: float = Field(..., ge=-1, le=1)
    signal: str = Field(..., description="BULLISH, BEARISH, NEUTRAL, INSUFFICIENT_DATA")


class SignalsDashboardResponse(TimestampMixin):
    """Response for signals dashboard endpoint."""
    ticker: str
    prediction: Optional[PredictionSignal] = None
    margin_risk: Optional[MarginRiskSignal] = None
    financial_health: Optional[FinancialHealthSignal] = None
    insider_sentiment: Optional[float] = Field(None, ge=-1, le=1)
    technical_trend: Optional[str] = None
    overall_signal: OverallSignal
    recommendation: str = Field(..., description="Human-readable recommendation")


# ============================================================================
# Alert Schemas
# ============================================================================

class AlertConfig(BaseModel):
    """Alert configuration."""
    margin_risk_threshold: float = Field(0.7, ge=0, le=1)
    insider_buy_threshold: float = Field(0.5, ge=0, le=1)
    volatility_spike_threshold: float = Field(2.0, ge=1)
    enabled: bool = True


class Alert(BaseModel):
    """Single alert."""
    alert_type: str = Field(..., description="margin_risk, insider, volatility, etc.")
    ticker: str
    severity: str = Field(..., description="LOW, MEDIUM, HIGH, CRITICAL")
    message: str
    value: float
    threshold: float
    triggered_at: datetime


class AlertsResponse(TimestampMixin):
    """Response for alerts endpoint."""
    alerts: List[Alert]
    count: int
    critical_count: int
    high_count: int
