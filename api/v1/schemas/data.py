"""
Pydantic schemas for data endpoints.
"""

from datetime import datetime, date
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, ConfigDict

from api.v1.schemas.common import DataPoint, OHLCV, TimestampMixin


# ============================================================================
# FRED Data Schemas
# ============================================================================

class FREDSeriesInfo(BaseModel):
    """FRED series metadata."""
    series_id: str = Field(..., description="FRED series identifier")
    title: Optional[str] = Field(None, description="Series title")
    frequency: Optional[str] = Field(None, description="Data frequency")
    units: Optional[str] = Field(None, description="Data units")
    seasonal_adjustment: Optional[str] = Field(None, description="Seasonal adjustment")
    last_updated: Optional[datetime] = None


class FREDDataResponse(TimestampMixin):
    """Response for FRED data endpoint."""
    series_id: str
    series_info: Optional[FREDSeriesInfo] = None
    data: List[DataPoint]
    count: int = Field(..., description="Number of data points")
    start_date: Optional[date] = None
    end_date: Optional[date] = None


# ============================================================================
# Stock Data Schemas
# ============================================================================

class StockQuote(BaseModel):
    """Current stock quote."""
    price: float
    change: float
    change_percent: float
    volume: int
    market_cap: Optional[float] = None
    pe_ratio: Optional[float] = None
    dividend_yield: Optional[float] = None


class StockDataResponse(TimestampMixin):
    """Response for stock data endpoint."""
    ticker: str
    quote: Optional[StockQuote] = None
    history: List[OHLCV]
    count: int
    period: str = Field(..., description="Data period: 1d, 5d, 1mo, etc.")


# ============================================================================
# Options Data Schemas
# ============================================================================

class OptionContract(BaseModel):
    """Single option contract."""
    contract_symbol: str
    strike: float
    expiration: date
    option_type: str = Field(..., description="call or put")
    last_price: float
    bid: float
    ask: float
    volume: int
    open_interest: int
    implied_volatility: float
    delta: Optional[float] = None
    gamma: Optional[float] = None
    theta: Optional[float] = None
    vega: Optional[float] = None
    
    model_config = ConfigDict(from_attributes=True)


class OptionsChainSummary(BaseModel):
    """Summary of options chain."""
    total_call_volume: int
    total_put_volume: int
    total_call_oi: int
    total_put_oi: int
    put_call_ratio_volume: float
    put_call_ratio_oi: float
    avg_iv_calls: Optional[float] = None
    avg_iv_puts: Optional[float] = None


class OptionsDataResponse(TimestampMixin):
    """Response for options data endpoint."""
    ticker: str
    underlying_price: float
    expirations: List[date]
    summary: OptionsChainSummary
    calls: List[OptionContract]
    puts: List[OptionContract]


# ============================================================================
# SEC Filing Schemas
# ============================================================================

class SECFiling(BaseModel):
    """SEC filing record."""
    accession_number: str
    form_type: str
    filing_date: date
    company_name: str
    cik: str
    description: Optional[str] = None
    url: Optional[str] = None
    
    model_config = ConfigDict(from_attributes=True)


class SECFilingResponse(TimestampMixin):
    """Response for SEC filings endpoint."""
    filings: List[SECFiling]
    count: int
    form_types: Optional[List[str]] = None


# ============================================================================
# Insider Trading Schemas
# ============================================================================

class InsiderTransaction(BaseModel):
    """Single insider transaction."""
    filing_date: date
    trade_date: date
    insider_name: str
    insider_title: Optional[str] = None
    transaction_type: str = Field(..., description="P (Purchase), S (Sale), etc.")
    shares: int
    price: Optional[float] = None
    value: Optional[float] = None
    shares_owned_after: Optional[int] = None
    
    model_config = ConfigDict(from_attributes=True)


class InsiderSummary(BaseModel):
    """Summary of insider activity."""
    net_shares: int = Field(..., description="Net shares (buys - sells)")
    net_value: float = Field(..., description="Net transaction value")
    buy_count: int
    sell_count: int
    unique_insiders: int


class InsiderDataResponse(TimestampMixin):
    """Response for insider trading endpoint."""
    ticker: str
    summary: InsiderSummary
    transactions: List[InsiderTransaction]
    period_days: int
