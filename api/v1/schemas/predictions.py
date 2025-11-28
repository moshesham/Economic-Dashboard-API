"""
Pydantic schemas for prediction endpoints.
"""

from datetime import datetime, date
from typing import Optional, Dict, List, Any
from pydantic import BaseModel, Field

from api.v1.schemas.common import TimestampMixin, SignalStrength


# ============================================================================
# Single Prediction
# ============================================================================

class PredictionMetrics(BaseModel):
    """Model performance metrics."""
    accuracy: Optional[float] = Field(None, ge=0, le=1)
    precision: Optional[float] = Field(None, ge=0, le=1)
    recall: Optional[float] = Field(None, ge=0, le=1)
    f1_score: Optional[float] = Field(None, ge=0, le=1)
    auc_roc: Optional[float] = Field(None, ge=0, le=1)


class PredictionResponse(TimestampMixin):
    """Response for single prediction endpoint."""
    ticker: str
    prediction: int = Field(..., description="1 for UP, 0 for DOWN")
    direction: str = Field(..., description="UP or DOWN")
    probability: float = Field(..., ge=0, le=1, description="Prediction probability")
    confidence: float = Field(..., ge=0, le=1, description="Model confidence")
    horizon: str = Field("5d", description="Prediction horizon")
    model_version: Optional[str] = None
    metrics: Optional[PredictionMetrics] = None
    features_used: Optional[int] = Field(None, description="Number of features")


# ============================================================================
# Multi-Horizon Predictions
# ============================================================================

class HorizonPrediction(BaseModel):
    """Prediction for a specific time horizon."""
    horizon: str = Field(..., description="Time horizon: 1d, 5d, 20d, etc.")
    prediction: int
    direction: str
    probability: float
    confidence: float


class MultiHorizonPredictionResponse(TimestampMixin):
    """Response for multi-horizon prediction endpoint."""
    ticker: str
    predictions: List[HorizonPrediction]
    consensus_direction: str = Field(..., description="Consensus across horizons")
    consensus_strength: float = Field(..., ge=0, le=1)
    divergence_alert: bool = Field(False, description="True if horizons disagree")


# ============================================================================
# SHAP Explanations
# ============================================================================

class FeatureContribution(BaseModel):
    """Single feature's contribution to prediction."""
    feature: str
    value: float = Field(..., description="Feature value")
    shap_value: float = Field(..., description="SHAP contribution")
    direction: str = Field(..., description="POSITIVE or NEGATIVE impact")
    importance_rank: int = Field(..., ge=1, description="Feature importance rank")


class SHAPExplanationResponse(TimestampMixin):
    """Response for SHAP explanation endpoint."""
    ticker: str
    prediction: int
    probability: float
    base_value: float = Field(..., description="Model base prediction")
    top_positive_features: List[FeatureContribution]
    top_negative_features: List[FeatureContribution]
    feature_count: int
    explanation_summary: str = Field(..., description="Human-readable explanation")


# ============================================================================
# Trading Signals
# ============================================================================

class StockSignal(BaseModel):
    """Trading signal for a single stock."""
    ticker: str
    prediction_signal: SignalStrength
    technical_signal: SignalStrength
    options_signal: Optional[SignalStrength] = None
    composite_signal: SignalStrength
    risk_score: float = Field(..., ge=0, le=1)
    last_updated: datetime


class TradingSignalsResponse(TimestampMixin):
    """Response for trading signals endpoint."""
    signals: List[StockSignal]
    market_regime: str = Field(..., description="Risk-On, Risk-Off, or Neutral")
    bullish_count: int
    bearish_count: int
    neutral_count: int
    high_confidence_picks: List[str] = Field(..., description="Tickers with high confidence")


# ============================================================================
# Prediction History
# ============================================================================

class PredictionHistoryPoint(BaseModel):
    """Historical prediction record."""
    date: date
    prediction: int
    actual: Optional[int] = None
    probability: float
    correct: Optional[bool] = None


class PredictionHistoryResponse(TimestampMixin):
    """Response for prediction history endpoint."""
    ticker: str
    history: List[PredictionHistoryPoint]
    accuracy: float = Field(..., ge=0, le=1)
    win_rate: float = Field(..., ge=0, le=1)
    total_predictions: int
    correct_predictions: int
