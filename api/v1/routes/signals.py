"""
Signals endpoints - Actionable trading signals and alerts.
"""

from fastapi import APIRouter, Query, HTTPException
from typing import Optional, List
from datetime import datetime

router = APIRouter()


# ============================================================================
# Margin Risk Signals
# ============================================================================

@router.get("/margin-risk/{ticker}")
async def get_margin_risk_signal(
    ticker: str,
):
    """
    Get margin call risk assessment for a stock.
    
    Composite risk score based on:
    - Leverage metrics (30% weight)
    - Volatility indicators (25% weight)
    - Options flow (25% weight)
    - Liquidity conditions (20% weight)
    
    Args:
        ticker: Stock ticker symbol
    
    Returns:
        Margin risk score with component breakdown
    """
    try:
        from modules.features.margin_risk_composite import MarginCallRiskCalculator
        
        calc = MarginCallRiskCalculator()
        risk = calc.calculate_composite_risk(ticker.upper())
        
        if not risk:
            raise HTTPException(
                status_code=404,
                detail=f"No margin risk data for ticker: {ticker}"
            )
        
        return {
            "ticker": ticker.upper(),
            "composite_risk_score": risk.get("composite_score"),
            "risk_level": risk.get("risk_level"),  # Low, Medium, High, Critical
            "components": risk.get("components"),
            "signal": risk.get("signal"),  # SAFE, CAUTION, WARNING, DANGER
            "last_updated": datetime.utcnow().isoformat(),
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/margin-risk")
async def get_all_margin_risk_signals(
    min_risk: float = Query(0.5, description="Minimum risk score to include"),
    limit: int = Query(20, description="Maximum number of results"),
):
    """
    Get margin risk signals for all monitored stocks.
    
    Returns stocks sorted by risk level for portfolio monitoring.
    
    Args:
        min_risk: Minimum risk score threshold
        limit: Maximum number of results
    
    Returns:
        List of stocks with elevated margin risk
    """
    try:
        from modules.database import get_db_connection
        
        db = get_db_connection()
        result = db.query(f"""
            SELECT 
                ticker,
                composite_score,
                risk_level,
                leverage_score,
                volatility_score,
                options_score,
                liquidity_score,
                calculated_at
            FROM margin_call_risk
            WHERE composite_score >= {min_risk}
            ORDER BY composite_score DESC
            LIMIT {limit}
        """)
        
        return {
            "signals": result.to_dict(orient='records') if not result.empty else [],
            "count": len(result),
            "threshold": min_risk,
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Insider Trading Signals
# ============================================================================

@router.get("/insider/{ticker}")
async def get_insider_signal(
    ticker: str,
    days: int = Query(30, description="Lookback period in days"),
):
    """
    Get insider trading sentiment signal for a stock.
    
    Analyzes SEC Form 4 filings to detect:
    - Net insider buying/selling
    - Unusual transaction patterns
    - Cluster buying (multiple insiders)
    - Large transaction alerts
    
    Args:
        ticker: Stock ticker symbol
        days: Lookback period in days
    
    Returns:
        Insider sentiment signal with transaction details
    """
    try:
        from modules.features.insider_trading_tracker import InsiderTradingTracker
        
        tracker = InsiderTradingTracker()
        sentiment = tracker.get_sentiment_analysis(ticker.upper(), days=days)
        
        if not sentiment:
            raise HTTPException(
                status_code=404,
                detail=f"No insider data for ticker: {ticker}"
            )
        
        return {
            "ticker": ticker.upper(),
            "sentiment_score": sentiment.get("score"),  # -1 to +1
            "signal": sentiment.get("signal"),  # BEARISH, NEUTRAL, BULLISH
            "net_shares": sentiment.get("net_shares"),
            "net_value": sentiment.get("net_value"),
            "transaction_count": sentiment.get("count"),
            "notable_transactions": sentiment.get("notable"),
            "period_days": days,
            "last_updated": datetime.utcnow().isoformat(),
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Sector Rotation Signals
# ============================================================================

@router.get("/sector-rotation")
async def get_sector_rotation_signals():
    """
    Get sector rotation analysis and signals.
    
    Tracks rotation across 11 S&P 500 sector ETFs:
    - Relative strength vs SPY
    - Momentum classification
    - Risk-on vs Risk-off positioning
    
    Returns:
        Sector rotation signals with rankings
    """
    try:
        from modules.features.sector_rotation_detector import SectorRotationDetector
        
        detector = SectorRotationDetector()
        rotation = detector.analyze_rotation()
        
        return {
            "market_regime": rotation.get("regime"),  # Risk-On, Risk-Off
            "sector_rankings": rotation.get("rankings"),
            "leading_sectors": rotation.get("leading"),
            "lagging_sectors": rotation.get("lagging"),
            "rotation_signal": rotation.get("signal"),
            "last_updated": datetime.utcnow().isoformat(),
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Combined Signals Dashboard
# ============================================================================

@router.get("/dashboard/{ticker}")
async def get_signals_dashboard(
    ticker: str,
):
    """
    Get all signals for a stock in one call.
    
    Aggregates:
    - ML prediction
    - Margin risk
    - Insider sentiment
    - Technical signals
    - Financial health
    
    Args:
        ticker: Stock ticker symbol
    
    Returns:
        Comprehensive signal dashboard
    """
    try:
        signals = {
            "ticker": ticker.upper(),
            "timestamp": datetime.utcnow().isoformat(),
        }
        
        # ML Prediction
        try:
            from modules.ml.prediction import PredictionEngine
            engine = PredictionEngine()
            pred = engine.predict(ticker=ticker.upper())
            signals["prediction"] = {
                "direction": "UP" if pred.get('prediction', 0) == 1 else "DOWN",
                "confidence": pred.get('confidence', 0.5),
            }
        except:
            signals["prediction"] = None
        
        # Margin Risk
        try:
            from modules.features.margin_risk_composite import MarginCallRiskCalculator
            calc = MarginCallRiskCalculator()
            risk = calc.calculate_composite_risk(ticker.upper())
            signals["margin_risk"] = {
                "score": risk.get("composite_score"),
                "level": risk.get("risk_level"),
            }
        except:
            signals["margin_risk"] = None
        
        # Financial Health
        try:
            from modules.features.financial_health_scorer import FinancialHealthScorer
            scorer = FinancialHealthScorer()
            health = scorer.calculate_composite_health_score(ticker.upper())
            signals["financial_health"] = {
                "score": health.get("composite_score"),
                "rating": health.get("health_rating"),
            }
        except:
            signals["financial_health"] = None
        
        # Overall signal
        signals["overall_signal"] = _calculate_overall_signal(signals)
        
        return signals
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def _calculate_overall_signal(signals: dict) -> dict:
    """Calculate an overall signal from component signals."""
    score = 0
    weights = 0
    
    # Prediction contributes
    if signals.get("prediction"):
        pred_score = 1 if signals["prediction"]["direction"] == "UP" else -1
        pred_score *= signals["prediction"]["confidence"]
        score += pred_score * 0.4
        weights += 0.4
    
    # Margin risk contributes (inverted - high risk is negative)
    if signals.get("margin_risk"):
        risk = signals["margin_risk"]["score"]
        risk_score = 1 - risk  # Invert: low risk = positive
        score += (risk_score - 0.5) * 0.3
        weights += 0.3
    
    # Financial health contributes
    if signals.get("financial_health"):
        health = signals["financial_health"]["score"] / 100  # Normalize to 0-1
        score += (health - 0.5) * 0.3
        weights += 0.3
    
    if weights > 0:
        final_score = score / weights
        if final_score > 0.2:
            signal = "BULLISH"
        elif final_score < -0.2:
            signal = "BEARISH"
        else:
            signal = "NEUTRAL"
        
        return {
            "score": round(final_score, 3),
            "signal": signal,
        }
    
    return {"score": 0, "signal": "INSUFFICIENT_DATA"}
