"""
Data endpoints - Access to raw economic data from various sources.
"""

from fastapi import APIRouter, Query, HTTPException
from typing import Optional, List
from datetime import datetime, timedelta
from pydantic import BaseModel

router = APIRouter()


# ============================================================================
# Pydantic Models
# ============================================================================

class FREDSeriesResponse(BaseModel):
    """Response model for FRED data."""
    series_id: str
    name: str
    data: List[dict]
    last_updated: Optional[datetime]
    frequency: str
    units: str


class StockDataResponse(BaseModel):
    """Response model for stock OHLCV data."""
    ticker: str
    data: List[dict]
    last_updated: Optional[datetime]


# ============================================================================
# FRED Data Endpoints
# ============================================================================

@router.get("/fred/{series_id}", response_model=FREDSeriesResponse)
async def get_fred_series(
    series_id: str,
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
):
    """
    Get FRED economic data for a specific series.
    
    Available series include:
    - GDP, GDPC1 (Real GDP)
    - CPIAUCSL (CPI), PCEPI (PCE)
    - UNRATE (Unemployment)
    - DGS10, DGS2 (Treasury yields)
    - And many more...
    
    Args:
        series_id: FRED series identifier
        start_date: Optional start date filter
        end_date: Optional end date filter
    
    Returns:
        Time series data with metadata
    """
    try:
        from modules.database import get_fred_series
        
        series_ids = [series_id.upper()]
        df = get_fred_series(series_ids, start_date=start_date, end_date=end_date)
        
        if df.empty:
            raise HTTPException(status_code=404, detail=f"No data found for series: {series_id}")
        
        # Convert to response format
        data = df.reset_index().to_dict(orient='records')
        
        return {
            "series_id": series_id.upper(),
            "name": series_id.upper(),  # TODO: Add series name lookup
            "data": data,
            "last_updated": datetime.utcnow(),
            "frequency": "daily",  # TODO: Get actual frequency
            "units": "various",  # TODO: Get actual units
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/fred")
async def list_available_fred_series():
    """
    List all available FRED series in the database.
    
    Returns:
        List of available series with metadata
    """
    try:
        from modules.database import get_db_connection
        
        db = get_db_connection()
        result = db.query("""
            SELECT DISTINCT 
                series_id,
                MIN(date) as start_date,
                MAX(date) as end_date,
                COUNT(*) as data_points
            FROM fred_data
            GROUP BY series_id
            ORDER BY series_id
        """)
        
        return {
            "series": result.to_dict(orient='records'),
            "count": len(result),
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Stock/Market Data Endpoints
# ============================================================================

@router.get("/stocks/{ticker}", response_model=StockDataResponse)
async def get_stock_data(
    ticker: str,
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    interval: str = Query("1d", description="Data interval: 1d, 1wk, 1mo"),
):
    """
    Get stock OHLCV data for a specific ticker.
    
    Args:
        ticker: Stock ticker symbol (e.g., AAPL, MSFT, SPY)
        start_date: Optional start date filter
        end_date: Optional end date filter
        interval: Data interval (1d, 1wk, 1mo)
    
    Returns:
        OHLCV time series data
    """
    try:
        from modules.database import get_stock_ohlcv
        
        df = get_stock_ohlcv(
            tickers=[ticker.upper()],
            start_date=start_date,
            end_date=end_date
        )
        
        if df.empty:
            raise HTTPException(status_code=404, detail=f"No data found for ticker: {ticker}")
        
        data = df.reset_index().to_dict(orient='records')
        
        return {
            "ticker": ticker.upper(),
            "data": data,
            "last_updated": datetime.utcnow(),
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stocks")
async def list_available_stocks():
    """
    List all available stock tickers in the database.
    
    Returns:
        List of available tickers with metadata
    """
    try:
        from modules.database import get_db_connection
        
        db = get_db_connection()
        result = db.query("""
            SELECT DISTINCT 
                ticker,
                MIN(date) as start_date,
                MAX(date) as end_date,
                COUNT(*) as data_points
            FROM yfinance_ohlcv
            GROUP BY ticker
            ORDER BY ticker
        """)
        
        return {
            "tickers": result.to_dict(orient='records'),
            "count": len(result),
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# SEC Data Endpoints
# ============================================================================

@router.get("/sec/filings/{ticker}")
async def get_sec_filings(
    ticker: str,
    form_type: Optional[str] = Query(None, description="Form type: 10-K, 10-Q, 8-K"),
    limit: int = Query(10, description="Number of filings to return"),
):
    """
    Get SEC filings for a company.
    
    Args:
        ticker: Stock ticker symbol
        form_type: Optional form type filter
        limit: Maximum number of results
    
    Returns:
        List of SEC filings with metadata
    """
    try:
        from modules.sec_data_loader import get_sec_filings
        
        filings = get_sec_filings(ticker.upper(), form_type=form_type, limit=limit)
        
        return {
            "ticker": ticker.upper(),
            "filings": filings,
            "count": len(filings) if filings else 0,
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sec/insider/{ticker}")
async def get_insider_transactions(
    ticker: str,
    days: int = Query(90, description="Number of days to look back"),
):
    """
    Get insider transactions from SEC Form 4 filings.
    
    Args:
        ticker: Stock ticker symbol
        days: Number of days to look back
    
    Returns:
        Insider transaction data with sentiment analysis
    """
    try:
        from modules.features.insider_trading_tracker import InsiderTradingTracker
        
        tracker = InsiderTradingTracker()
        transactions = tracker.get_recent_transactions(ticker.upper(), days=days)
        sentiment = tracker.calculate_sentiment_score(ticker.upper())
        
        return {
            "ticker": ticker.upper(),
            "transactions": transactions,
            "sentiment": sentiment,
            "period_days": days,
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
