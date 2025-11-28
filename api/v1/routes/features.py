"""
Features endpoints - Access to pre-computed feature engineering data.
"""

from fastapi import APIRouter, Query, HTTPException
from typing import Optional, List
from datetime import datetime

router = APIRouter()


# ============================================================================
# Technical Features
# ============================================================================

@router.get("/technical/{ticker}")
async def get_technical_features(
    ticker: str,
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    indicators: Optional[List[str]] = Query(None, description="Specific indicators to return"),
):
    """
    Get pre-computed technical indicators for a stock.
    
    Available indicators:
    - RSI (5, 14, 28 periods)
    - MACD (line, signal, histogram)
    - Bollinger Bands (upper, middle, lower, %B)
    - Moving Averages (SMA/EMA 10, 20, 50, 100, 200)
    - ADX, ATR, OBV, MFI, CMF
    - Stochastic Oscillator
    
    Args:
        ticker: Stock ticker symbol
        start_date: Optional start date filter
        end_date: Optional end date filter
        indicators: Optional list of specific indicators to return
    
    Returns:
        Technical indicator values with timestamps
    """
    try:
        from modules.database import get_technical_features
        
        df = get_technical_features(
            ticker=ticker.upper(),
            start_date=start_date,
            end_date=end_date
        )
        
        if df.empty:
            # Try to calculate on-demand if not cached
            from modules.features.technical_indicators import TechnicalIndicatorCalculator
            calc = TechnicalIndicatorCalculator()
            df = calc.calculate_all_indicators(ticker.upper())
            
            if df.empty:
                raise HTTPException(
                    status_code=404, 
                    detail=f"No technical features found for ticker: {ticker}"
                )
        
        # Filter to specific indicators if requested
        if indicators:
            available_cols = ['date', 'ticker'] + [c for c in df.columns if c not in ['date', 'ticker']]
            selected_cols = ['date', 'ticker'] + [c for c in indicators if c in available_cols]
            df = df[selected_cols]
        
        data = df.to_dict(orient='records')
        
        return {
            "ticker": ticker.upper(),
            "features": data,
            "available_indicators": [c for c in df.columns if c not in ['date', 'ticker']],
            "count": len(data),
            "last_updated": datetime.utcnow().isoformat(),
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Options Features
# ============================================================================

@router.get("/options/{ticker}")
async def get_options_features(
    ticker: str,
    date: Optional[str] = Query(None, description="Specific date (YYYY-MM-DD)"),
):
    """
    Get options-derived features for a stock.
    
    Features include:
    - Put/Call ratio (volume and open interest)
    - Implied volatility metrics (mean, skew)
    - IV Rank and IV Percentile
    - Options flow indicators
    
    Args:
        ticker: Stock ticker symbol
        date: Optional specific date
    
    Returns:
        Options-derived features and metrics
    """
    try:
        from modules.features.options_metrics import OptionsMetricsCalculator
        
        calc = OptionsMetricsCalculator()
        metrics = calc.fetch_options_data(ticker.upper(), date=date)
        
        if not metrics:
            raise HTTPException(
                status_code=404,
                detail=f"No options data found for ticker: {ticker}"
            )
        
        return {
            "ticker": ticker.upper(),
            "metrics": metrics,
            "date": date or datetime.utcnow().strftime("%Y-%m-%d"),
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Derived Features
# ============================================================================

@router.get("/derived/{ticker}")
async def get_derived_features(
    ticker: str,
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
):
    """
    Get derived/composite features for a stock.
    
    Features include:
    - Z-scores of all indicators
    - Momentum regime classification
    - Volatility regime classification
    - Feature interactions (RSI×Volume, MACD×ATR)
    - Cross-timeframe features
    
    Args:
        ticker: Stock ticker symbol
        start_date: Optional start date filter
        end_date: Optional end date filter
    
    Returns:
        Derived feature values
    """
    try:
        from modules.features.derived_features import DerivedFeaturesCalculator
        
        calc = DerivedFeaturesCalculator()
        df = calc.calculate_all_derived_features(
            ticker=ticker.upper(),
            start_date=start_date,
            end_date=end_date
        )
        
        if df is None or df.empty:
            raise HTTPException(
                status_code=404,
                detail=f"No derived features found for ticker: {ticker}"
            )
        
        return {
            "ticker": ticker.upper(),
            "features": df.to_dict(orient='records'),
            "count": len(df),
            "last_updated": datetime.utcnow().isoformat(),
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Financial Health Features
# ============================================================================

@router.get("/health-score/{ticker}")
async def get_financial_health_score(
    ticker: str,
):
    """
    Get financial health scores for a company.
    
    Scores include:
    - Piotroski F-Score (0-9): Fundamental strength
    - Altman Z-Score: Bankruptcy risk
    - Composite health rating
    
    Args:
        ticker: Stock ticker symbol
    
    Returns:
        Financial health scores with breakdown
    """
    try:
        from modules.features.financial_health_scorer import FinancialHealthScorer
        
        scorer = FinancialHealthScorer()
        composite = scorer.calculate_composite_health_score(ticker.upper())
        
        if 'error' in composite:
            raise HTTPException(
                status_code=404,
                detail=composite['error']
            )
        
        return composite
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Cross-Asset Correlation (NEW)
# ============================================================================

@router.get("/correlations/{ticker}")
async def get_cross_asset_correlations(
    ticker: str,
    window: int = Query(60, description="Rolling window in days"),
    assets: Optional[List[str]] = Query(
        None, 
        description="Assets to correlate with (default: SPY, TLT, GLD, UUP)"
    ),
):
    """
    Get cross-asset correlation analysis.
    
    NEW GROUNDBREAKING FEATURE:
    Analyzes correlation regime between the ticker and major asset classes
    to identify correlation breakdowns that signal market stress.
    
    Args:
        ticker: Stock ticker symbol
        window: Rolling correlation window in days
        assets: List of assets to correlate with
    
    Returns:
        Rolling correlations and regime analysis
    """
    try:
        # Default assets for correlation analysis
        if not assets:
            assets = ['SPY', 'TLT', 'GLD', 'UUP', 'VIX']
        
        from modules.features.cross_asset_correlations import CrossAssetCorrelationAnalyzer
        
        analyzer = CrossAssetCorrelationAnalyzer()
        result = analyzer.analyze_correlations(
            ticker=ticker.upper(),
            comparison_assets=assets,
            window=window
        )
        
        return {
            "ticker": ticker.upper(),
            "correlations": result,
            "window": window,
            "assets": assets,
            "last_updated": datetime.utcnow().isoformat(),
        }
        
    except ImportError:
        # Module not yet implemented
        raise HTTPException(
            status_code=501,
            detail="Cross-asset correlation module not yet implemented"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
