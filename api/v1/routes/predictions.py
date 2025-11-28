"""
Predictions endpoints - ML-powered predictions with explainability.
"""

from fastapi import APIRouter, Query, HTTPException
from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel

router = APIRouter()


# ============================================================================
# Pydantic Models
# ============================================================================

class PredictionResult(BaseModel):
    """Single prediction result."""
    ticker: str
    prediction_date: str
    horizon: str  # 1d, 5d, 20d
    direction: str  # UP, DOWN
    confidence: float
    probability: float
    model_type: str


class PredictionExplanation(BaseModel):
    """SHAP-based prediction explanation."""
    feature: str
    importance: float
    value: float
    contribution: str  # positive, negative


# ============================================================================
# Stock Predictions
# ============================================================================

@router.get("/stock/{ticker}")
async def get_stock_prediction(
    ticker: str,
    horizon: str = Query("1d", description="Prediction horizon: 1d, 5d, 20d"),
    model: str = Query("ensemble", description="Model type: xgboost, lightgbm, ensemble"),
    include_explanation: bool = Query(True, description="Include SHAP explanation"),
):
    """
    Get ML prediction for a stock.
    
    Multi-horizon predictions with confidence scores and SHAP explainability.
    
    Args:
        ticker: Stock ticker symbol
        horizon: Prediction horizon (1d, 5d, 20d)
        model: Model type to use
        include_explanation: Whether to include SHAP feature importance
    
    Returns:
        Prediction with confidence and optional explanation
    """
    try:
        from modules.ml.prediction import PredictionEngine
        
        engine = PredictionEngine()
        prediction = engine.predict(
            ticker=ticker.upper(),
            model_type=model,
        )
        
        if not prediction:
            raise HTTPException(
                status_code=404,
                detail=f"No prediction available for ticker: {ticker}"
            )
        
        result = {
            "ticker": ticker.upper(),
            "prediction_date": datetime.utcnow().strftime("%Y-%m-%d"),
            "horizon": horizon,
            "direction": "UP" if prediction.get('prediction', 0) == 1 else "DOWN",
            "confidence": prediction.get('confidence', 0.5),
            "probability": prediction.get('probability', 0.5),
            "model_type": model,
        }
        
        # Add SHAP explanation if requested
        if include_explanation:
            explanation = engine.explain_prediction(ticker.upper())
            result["explanation"] = explanation
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stock/{ticker}/history")
async def get_prediction_history(
    ticker: str,
    days: int = Query(30, description="Number of days of history"),
):
    """
    Get historical predictions with accuracy metrics.
    
    Args:
        ticker: Stock ticker symbol
        days: Number of days of history
    
    Returns:
        Historical predictions with actual outcomes and accuracy
    """
    try:
        from modules.database import get_db_connection
        
        db = get_db_connection()
        result = db.query(f"""
            SELECT 
                prediction_date,
                ticker,
                model_type,
                prediction,
                probability,
                actual_outcome,
                CASE WHEN prediction = actual_outcome THEN 1 ELSE 0 END as correct
            FROM ml_predictions
            WHERE ticker = '{ticker.upper()}'
              AND prediction_date >= CURRENT_DATE - INTERVAL '{days} days'
            ORDER BY prediction_date DESC
        """)
        
        if result.empty:
            return {
                "ticker": ticker.upper(),
                "predictions": [],
                "accuracy": None,
                "count": 0,
            }
        
        # Calculate rolling accuracy
        accuracy = result['correct'].mean() if 'correct' in result.columns else None
        
        return {
            "ticker": ticker.upper(),
            "predictions": result.to_dict(orient='records'),
            "accuracy": accuracy,
            "count": len(result),
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Multi-Horizon Predictions (NEW)
# ============================================================================

@router.get("/multi-horizon/{ticker}")
async def get_multi_horizon_predictions(
    ticker: str,
    include_explanation: bool = Query(True, description="Include SHAP explanation"),
):
    """
    Get predictions for multiple horizons simultaneously.
    
    NEW GROUNDBREAKING FEATURE:
    Returns predictions for 1-day, 5-day, and 20-day horizons with
    confidence intervals and cross-horizon consistency analysis.
    
    Args:
        ticker: Stock ticker symbol
        include_explanation: Whether to include SHAP feature importance
    
    Returns:
        Multi-horizon predictions with confidence and consistency
    """
    try:
        from modules.ml.multi_horizon import MultiHorizonPredictor
        
        predictor = MultiHorizonPredictor()
        predictions = predictor.predict_all_horizons(ticker.upper())
        
        return {
            "ticker": ticker.upper(),
            "prediction_date": datetime.utcnow().strftime("%Y-%m-%d"),
            "horizons": {
                "1d": predictions.get("1d"),
                "5d": predictions.get("5d"),
                "20d": predictions.get("20d"),
            },
            "consistency": predictions.get("consistency"),  # Are all horizons aligned?
            "confidence": predictions.get("overall_confidence"),
        }
        
    except ImportError:
        # Fallback to single horizon if multi-horizon not implemented
        try:
            from modules.ml.prediction import PredictionEngine
            
            engine = PredictionEngine()
            prediction = engine.predict(ticker=ticker.upper())
            
            return {
                "ticker": ticker.upper(),
                "prediction_date": datetime.utcnow().strftime("%Y-%m-%d"),
                "horizons": {
                    "1d": {
                        "direction": "UP" if prediction.get('prediction', 0) == 1 else "DOWN",
                        "confidence": prediction.get('confidence', 0.5),
                    },
                    "5d": None,
                    "20d": None,
                },
                "consistency": None,
                "confidence": prediction.get('confidence', 0.5),
                "note": "Multi-horizon module not yet implemented. Using single horizon.",
            }
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Recession Probability
# ============================================================================

@router.get("/recession")
async def get_recession_probability():
    """
    Get current recession probability from the recession model.
    
    Uses a multi-factor model combining:
    - Yield curve signals (25% weight)
    - Labor market indicators (20% weight)
    - Financial stress indicators (15% weight)
    - Economic activity (15% weight)
    - Consumer indicators (10% weight)
    - Housing market (10% weight)
    - Market signals (5% weight)
    
    Returns:
        Recession probability with component breakdown
    """
    try:
        from modules.ml.recession_model import RecessionModel
        
        model = RecessionModel()
        result = model.calculate_recession_probability()
        
        return {
            "probability": result.get("probability"),
            "risk_level": result.get("risk_level"),
            "components": result.get("components"),
            "historical_accuracy": result.get("historical_accuracy"),
            "last_updated": datetime.utcnow().isoformat(),
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Market Regime Detection (NEW)
# ============================================================================

@router.get("/regime")
async def get_market_regime():
    """
    Detect current market regime using Hidden Markov Models.
    
    NEW GROUNDBREAKING FEATURE:
    Uses HMM + Gaussian Mixture Models to identify:
    - Bull market regime
    - Bear market regime  
    - Sideways/consolidation regime
    - Transition probabilities
    
    Returns:
        Current regime with transition probabilities
    """
    try:
        from modules.ml.regime_model import MarketRegimeDetector
        
        detector = MarketRegimeDetector()
        regime = detector.detect_current_regime()
        
        return {
            "current_regime": regime.get("regime"),
            "confidence": regime.get("confidence"),
            "regime_duration_days": regime.get("duration"),
            "transition_probabilities": regime.get("transitions"),
            "historical_regimes": regime.get("history"),
            "last_updated": datetime.utcnow().isoformat(),
        }
        
    except ImportError:
        raise HTTPException(
            status_code=501,
            detail="Market regime detection module not yet implemented"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
