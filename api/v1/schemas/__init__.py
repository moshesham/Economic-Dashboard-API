"""
Pydantic schemas for API request/response validation.
"""

from api.v1.schemas.data import (
    FREDDataResponse,
    StockDataResponse,
    OptionsDataResponse,
    SECFilingResponse,
    InsiderDataResponse,
)
from api.v1.schemas.features import (
    TechnicalFeaturesResponse,
    OptionsFeaturesResponse,
    DerivedFeaturesResponse,
    AllFeaturesResponse,
)
from api.v1.schemas.predictions import (
    PredictionResponse,
    MultiHorizonPredictionResponse,
    SHAPExplanationResponse,
    TradingSignalsResponse,
)
from api.v1.schemas.signals import (
    MarginRiskResponse,
    InsiderSignalResponse,
    SectorRotationResponse,
    SignalsDashboardResponse,
)
from api.v1.schemas.portfolio import (
    PortfolioPosition,
    PortfolioRequest,
    OptimizationResponse,
    EfficientFrontierResponse,
    PortfolioAnalysisResponse,
    RebalanceResponse,
    RiskParityResponse,
)

__all__ = [
    # Data
    "FREDDataResponse",
    "StockDataResponse",
    "OptionsDataResponse",
    "SECFilingResponse",
    "InsiderDataResponse",
    # Features
    "TechnicalFeaturesResponse",
    "OptionsFeaturesResponse",
    "DerivedFeaturesResponse",
    "AllFeaturesResponse",
    # Predictions
    "PredictionResponse",
    "MultiHorizonPredictionResponse",
    "SHAPExplanationResponse",
    "TradingSignalsResponse",
    # Signals
    "MarginRiskResponse",
    "InsiderSignalResponse",
    "SectorRotationResponse",
    "SignalsDashboardResponse",
    # Portfolio
    "PortfolioPosition",
    "PortfolioRequest",
    "OptimizationResponse",
    "EfficientFrontierResponse",
    "PortfolioAnalysisResponse",
    "RebalanceResponse",
    "RiskParityResponse",
]
