"""
Common schema components shared across multiple endpoints.
"""

from datetime import datetime, date
from typing import Optional, List, Dict, Any, Generic, TypeVar
from pydantic import BaseModel, Field, ConfigDict

T = TypeVar("T")


class TimestampMixin(BaseModel):
    """Mixin for responses with timestamps."""
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    

class PaginationMixin(BaseModel):
    """Mixin for paginated responses."""
    page: int = Field(1, ge=1)
    page_size: int = Field(50, ge=1, le=500)
    total_count: int = Field(0, ge=0)
    total_pages: int = Field(0, ge=0)


class ErrorResponse(BaseModel):
    """Standard error response."""
    error: str
    detail: Optional[str] = None
    code: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class HealthStatus(BaseModel):
    """Health check response."""
    status: str = Field(..., description="Service status: healthy, degraded, unhealthy")
    version: str = Field(..., description="API version")
    uptime_seconds: float = Field(..., description="Service uptime in seconds")
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class ReadinessStatus(BaseModel):
    """Readiness check response."""
    ready: bool
    checks: Dict[str, bool] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class DataPoint(BaseModel):
    """Generic time-series data point."""
    date: date
    value: float
    
    model_config = ConfigDict(from_attributes=True)


class OHLCV(BaseModel):
    """OHLCV price data point."""
    date: date
    open: float
    high: float
    low: float
    close: float
    volume: int
    
    model_config = ConfigDict(from_attributes=True)


class TickerInfo(BaseModel):
    """Basic ticker information."""
    ticker: str = Field(..., description="Stock ticker symbol")
    name: Optional[str] = Field(None, description="Company name")
    sector: Optional[str] = Field(None, description="Sector classification")
    industry: Optional[str] = Field(None, description="Industry classification")


class RiskLevel(BaseModel):
    """Risk level classification."""
    score: float = Field(..., ge=0, le=1, description="Risk score 0-1")
    level: str = Field(..., description="Risk level: Low, Medium, High, Critical")
    
    @classmethod
    def from_score(cls, score: float) -> "RiskLevel":
        if score < 0.25:
            level = "Low"
        elif score < 0.5:
            level = "Medium"
        elif score < 0.75:
            level = "High"
        else:
            level = "Critical"
        return cls(score=score, level=level)


class SignalStrength(BaseModel):
    """Trading signal strength."""
    signal: str = Field(..., description="Signal: BULLISH, BEARISH, NEUTRAL")
    strength: float = Field(..., ge=-1, le=1, description="Signal strength -1 to +1")
    confidence: float = Field(..., ge=0, le=1, description="Confidence level 0-1")
