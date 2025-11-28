"""
Pydantic schemas for portfolio endpoints.
"""

from datetime import datetime
from typing import Optional, Dict, List, Any
from pydantic import BaseModel, Field, field_validator

from api.v1.schemas.common import TimestampMixin


# ============================================================================
# Request Schemas
# ============================================================================

class PortfolioPosition(BaseModel):
    """Single portfolio position."""
    ticker: str = Field(..., description="Stock ticker symbol")
    weight: float = Field(..., ge=0, le=1, description="Portfolio weight (0-1)")
    
    @field_validator('ticker')
    @classmethod
    def uppercase_ticker(cls, v: str) -> str:
        return v.upper()


class PortfolioRequest(BaseModel):
    """Portfolio optimization request."""
    tickers: List[str] = Field(..., min_length=2, max_length=50)
    target_return: Optional[float] = Field(None, description="Target annual return")
    max_volatility: Optional[float] = Field(None, description="Maximum volatility")
    risk_free_rate: float = Field(0.05, ge=0, le=0.2, description="Risk-free rate")
    min_weight: float = Field(0.0, ge=0, le=0.5, description="Minimum weight per asset")
    max_weight: float = Field(1.0, ge=0.1, le=1.0, description="Maximum weight per asset")
    
    @field_validator('tickers')
    @classmethod
    def uppercase_tickers(cls, v: List[str]) -> List[str]:
        return [t.upper() for t in v]


class RebalanceRequest(BaseModel):
    """Portfolio rebalancing request."""
    current_positions: List[PortfolioPosition]
    target_weights: List[PortfolioPosition]
    cash: float = Field(0, ge=0, description="Available cash")
    min_trade_value: float = Field(100, ge=0, description="Minimum trade value")


# ============================================================================
# Response Schemas - Optimization
# ============================================================================

class PortfolioMetrics(BaseModel):
    """Portfolio risk/return metrics."""
    expected_return: float = Field(..., description="Annualized expected return")
    volatility: float = Field(..., description="Annualized volatility")
    sharpe_ratio: float = Field(..., description="Sharpe ratio")
    sortino_ratio: Optional[float] = Field(None, description="Sortino ratio")
    max_drawdown: Optional[float] = Field(None, description="Maximum drawdown")
    calmar_ratio: Optional[float] = Field(None, description="Calmar ratio")


class AssetStats(BaseModel):
    """Individual asset statistics."""
    ticker: str
    expected_return: float
    volatility: float
    weight: float
    contribution_to_risk: Optional[float] = None
    correlation_to_portfolio: Optional[float] = None


class OptimizationResponse(TimestampMixin):
    """Response for portfolio optimization endpoint."""
    optimization_status: str = Field(..., description="success, partial, failed")
    optimal_weights: Dict[str, float]
    metrics: PortfolioMetrics
    individual_stats: Dict[str, AssetStats]
    constraints_satisfied: bool = True
    iterations: Optional[int] = None


# ============================================================================
# Response Schemas - Efficient Frontier
# ============================================================================

class FrontierPoint(BaseModel):
    """Single point on efficient frontier."""
    expected_return: float
    volatility: float
    sharpe_ratio: float
    weights: Dict[str, float]


class SpecialPortfolios(BaseModel):
    """Special portfolios on the frontier."""
    max_sharpe: FrontierPoint
    min_volatility: FrontierPoint
    max_return: Optional[FrontierPoint] = None


class EfficientFrontierResponse(TimestampMixin):
    """Response for efficient frontier endpoint."""
    frontier: List[FrontierPoint]
    special_portfolios: SpecialPortfolios
    frontier_points: int


# ============================================================================
# Response Schemas - Analysis
# ============================================================================

class RiskMetrics(BaseModel):
    """Portfolio risk metrics."""
    annual_volatility: float
    daily_volatility: float
    var_95_daily: float = Field(..., description="95% Value at Risk (daily)")
    cvar_95_daily: float = Field(..., description="95% Conditional VaR (daily)")
    var_99_daily: Optional[float] = Field(None, description="99% VaR (daily)")
    max_drawdown: float
    beta: Optional[float] = Field(None, description="Portfolio beta to market")
    tracking_error: Optional[float] = None


class ConcentrationMetrics(BaseModel):
    """Portfolio concentration metrics."""
    hhi: float = Field(..., description="Herfindahl-Hirschman Index")
    effective_n: float = Field(..., description="Effective number of stocks")
    top_3_weight: float = Field(..., description="Weight of top 3 holdings")
    max_single_weight: float


class SectorExposure(BaseModel):
    """Sector allocation."""
    sector: str
    weight: float
    count: int


class PortfolioAnalysisResponse(TimestampMixin):
    """Response for portfolio analysis endpoint."""
    risk_metrics: RiskMetrics
    concentration: ConcentrationMetrics
    sector_exposure: Optional[List[SectorExposure]] = None
    correlation_matrix: Dict[str, Dict[str, float]]
    diversification_ratio: Optional[float] = None


# ============================================================================
# Response Schemas - Rebalancing
# ============================================================================

class RebalanceTrade(BaseModel):
    """Single rebalancing trade."""
    ticker: str
    current_weight: float
    target_weight: float
    weight_change: float
    action: str = Field(..., description="BUY or SELL")
    priority: int = Field(..., description="Trade execution priority")


class RebalanceResponse(TimestampMixin):
    """Response for rebalancing endpoint."""
    trades: List[RebalanceTrade]
    trade_count: int
    buy_count: int
    sell_count: int
    total_turnover: float = Field(..., description="Sum of absolute weight changes")
    estimated_trades: Optional[int] = Field(None, description="Number of actual trades needed")


# ============================================================================
# Response Schemas - Risk Parity
# ============================================================================

class RiskContribution(BaseModel):
    """Asset's contribution to portfolio risk."""
    ticker: str
    weight: float
    risk_contribution: float = Field(..., description="Contribution to total risk")
    marginal_risk: Optional[float] = None


class RiskParityResponse(TimestampMixin):
    """Response for risk parity endpoint."""
    weights: Dict[str, float]
    risk_contributions: Dict[str, float]
    portfolio_volatility: float
    optimization_success: bool
    contribution_equality: float = Field(
        ..., 
        description="How equal are risk contributions (0=equal, higher=unequal)"
    )
    assets: List[RiskContribution]


# ============================================================================
# Response Schemas - Backtesting
# ============================================================================

class BacktestPeriod(BaseModel):
    """Backtest period statistics."""
    start_date: str
    end_date: str
    total_return: float
    annualized_return: float
    volatility: float
    sharpe_ratio: float
    max_drawdown: float
    win_rate: Optional[float] = None


class BacktestResponse(TimestampMixin):
    """Response for backtest endpoint."""
    strategy_name: str
    periods: List[BacktestPeriod]
    overall_metrics: PortfolioMetrics
    vs_benchmark: Optional[Dict[str, float]] = Field(
        None, 
        description="Performance relative to benchmark"
    )
    rebalance_count: int
    total_turnover: float
