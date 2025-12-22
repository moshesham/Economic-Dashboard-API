"""
ML Prediction Engine

Generates predictions for stock movements using trained models.
Provides confidence scoring and ensemble agreement metrics.
"""

import os
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from functools import lru_cache
from typing import Dict, List, Optional, Tuple, Any
from pathlib import Path
import logging
import pickle

from .models import BaseModel, XGBoostModel, LightGBMModel, EnsembleModel
from .feature_engineering import FeatureEngineer
from modules.database.factory import get_db_connection, get_backend

logger = logging.getLogger(__name__)


# LRU cache for loaded models (module-level for cross-engine reuse)
@lru_cache(maxsize=32)
def _load_model_cached(model_path: str, mtime: float) -> BaseModel:
    """
    Load a model from disk with LRU caching.
    
    The mtime argument ensures cache invalidation when the file changes.
    """
    with open(model_path, 'rb') as f:
        payload = pickle.load(f)

    if isinstance(payload, dict) and 'base_model_paths' in payload:
        model: BaseModel = EnsembleModel()
        model.load(model_path)
    elif isinstance(payload, dict) and payload.get('model_name') == 'XGBoost':
        model = XGBoostModel()
        model.load(model_path)
    elif isinstance(payload, dict) and payload.get('model_name') == 'LightGBM':
        model = LightGBMModel()
        model.load(model_path)
    else:
        # Fallback: treat the pickle as a full model object.
        model = payload

    logger.info(f"Loaded model from {model_path} (mtime={mtime})")
    return model


class PredictionEngine:
    """
    Handles prediction generation for stock movements.
    
    Features:
    - Load trained models with LRU caching
    - Generate predictions with confidence scores
    - Multi-model ensemble predictions
    - Prediction persistence to database
    - Historical prediction tracking
    """
    
    def __init__(
        self,
        db_path: str = "data/duckdb/economic_dashboard.duckdb",
        models_dir: str = "data/models"
    ):
        """
        Initialize the prediction engine.
        
        Args:
            db_path: Path to DuckDB database
            models_dir: Directory containing trained models
        """
        # Backwards-compat: callers may pass a DuckDB path.
        self.db_path = db_path
        if os.getenv('DATABASE_BACKEND', 'duckdb').lower() == 'duckdb' and not os.getenv('DUCKDB_PATH'):
            os.environ['DUCKDB_PATH'] = db_path
        self.models_dir = Path(models_dir)
        # Instance cache is kept for backwards compatibility but prefers the LRU cache
        self.loaded_models: Dict[str, BaseModel] = {}
        
    def load_model(self, model_path: str, cache_key: Optional[str] = None) -> BaseModel:
        """
        Load a trained model from disk (LRU cached).
        
        Args:
            model_path: Path to saved model file
            cache_key: Optional key (unused; kept for API compat)
            
        Returns:
            Loaded model instance
        """
        path = Path(model_path)
        if not path.exists():
            raise FileNotFoundError(f"Model file not found: {model_path}")

        mtime = path.stat().st_mtime
        model = _load_model_cached(str(path.resolve()), mtime)
        return model
    
    def get_latest_features(
        self,
        ticker: str,
        as_of_date: Optional[str] = None
    ) -> pd.DataFrame:
        """
        Get the latest feature values for a ticker.
        
        Args:
            ticker: Stock ticker symbol
            as_of_date: Optional date to get features as of (YYYY-MM-DD)
            
        Returns:
            DataFrame with latest features (single row)
        """
        db = get_db_connection()

        date_filter = f"AND date <= '{as_of_date}'" if as_of_date else ""
        # Pull a lookback window to compute rolling features.
        query = f"""
        SELECT date, open, high, low, close, volume
        FROM yfinance_ohlcv
        WHERE ticker = '{ticker}'
        {date_filter}
        ORDER BY date DESC
        LIMIT 600
        """
        price_df = db.query(query)
        if price_df.empty:
            raise ValueError(f"No OHLCV data found for {ticker} in yfinance_ohlcv")

        price_df['date'] = pd.to_datetime(price_df['date'])
        price_df = price_df.sort_values('date').set_index('date')

        engineer = FeatureEngineer()
        features = engineer.generate_all_features(price_df[['open', 'high', 'low', 'close', 'volume']])
        features = features.replace([np.inf, -np.inf], np.nan)

        # Use the last available row.
        X = features.tail(1).copy()
        X = X.fillna(X.median(numeric_only=True))
        logger.info(f"Retrieved OHLCV-derived features for {ticker} as of {X.index[0].date()}")
        return X
    
    def predict(
        self,
        ticker: str,
        model_path: Optional[str] = None,
        model_type: str = 'ensemble',
        as_of_date: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate prediction for a ticker.
        
        Args:
            ticker: Stock ticker symbol
            model_path: Path to trained model (auto-detected if None)
            model_type: Type of model if auto-detecting
            as_of_date: Date to generate prediction as of
            
        Returns:
            Dictionary with prediction results
        """
        # Auto-detect model path if not provided
        if model_path is None:
            pattern = f"{ticker}_{model_type}_*.pkl"
            model_files = list(self.models_dir.glob(pattern))
            
            if not model_files:
                raise FileNotFoundError(f"No trained model found for {ticker} ({model_type})")
            
            # Use most recent model
            model_path = str(sorted(model_files)[-1])
            logger.info(f"Auto-selected model: {model_path}")
        
        # Load model
        cache_key = f"{ticker}_{model_type}"
        model = self.load_model(model_path, cache_key)
        
        # Get latest features
        X = self.get_latest_features(ticker, as_of_date)

        # Align features to the model's expected feature set.
        if hasattr(model, 'feature_names') and model.feature_names:
            for col in model.feature_names:
                if col not in X.columns:
                    X[col] = 0.0
            X = X[model.feature_names]
        
        # Generate prediction
        prediction = model.predict(X)[0]
        probabilities = model.predict_proba(X)[0]
        
        # Calculate confidence (max probability)
        confidence = float(max(probabilities))
        
        # Get feature importance if available
        feature_importance = None
        try:
            importance = model.get_feature_importance()
            if importance is not None:
                # Expected: DataFrame with columns ['feature', 'importance']
                if isinstance(importance, pd.DataFrame) and {'feature', 'importance'}.issubset(importance.columns):
                    top = importance.sort_values('importance', ascending=False).head(10)
                    feature_importance = dict(zip(top['feature'].astype(str), top['importance'].astype(float)))
                # Fallback: dict-like
                elif isinstance(importance, dict):
                    top_features = sorted(importance.items(), key=lambda x: x[1], reverse=True)[:10]
                    feature_importance = dict(top_features)
        except Exception as e:
            logger.warning(f"Could not get feature importance: {e}")
        
        result = {
            'ticker': ticker,
            'prediction': int(prediction),
            'prediction_label': 'UP' if prediction == 1 else 'DOWN',
            'probability_down': float(probabilities[0]),
            'probability_up': float(probabilities[1]),
            'probability': float(probabilities[1]),
            'confidence': confidence,
            'model_type': model_type,
            'model_path': model_path,
            'prediction_date': datetime.now().isoformat(),
            'as_of_date': as_of_date or datetime.now().date().isoformat(),
            'feature_importance': feature_importance
        }
        
        logger.info(f"{ticker} prediction: {result['prediction_label']} "
                   f"(confidence: {confidence:.2%})")
        
        return result

    def explain_prediction(
        self,
        ticker: str,
        model_type: str = 'ensemble',
        as_of_date: Optional[str] = None,
        top_n: int = 10,
    ) -> List[Dict[str, Any]]:
        """Return a lightweight explanation payload for the API.

        Tries SHAP for tree models; falls back to feature importance.
        """
        # Load model (auto-detect most recent)
        pattern = f"{ticker}_{model_type}_*.pkl"
        model_files = list(self.models_dir.glob(pattern))
        if not model_files:
            return []
        model_path = str(sorted(model_files)[-1])
        model = self.load_model(model_path, cache_key=f"{ticker}_{model_type}")

        X = self.get_latest_features(ticker, as_of_date)
        if hasattr(model, 'feature_names') and model.feature_names:
            for col in model.feature_names:
                if col not in X.columns:
                    X[col] = 0.0
            X = X[model.feature_names]

        try:
            import shap

            if isinstance(model, EnsembleModel):
                # Average absolute SHAP across base models that support it.
                shap_vals = []
                for base in getattr(model, 'base_models', []):
                    explainer = shap.TreeExplainer(getattr(base, 'model', None))
                    sv = explainer.shap_values(X)
                    if isinstance(sv, list):
                        sv = sv[1] if len(sv) > 1 else sv[0]
                    shap_vals.append(np.abs(np.asarray(sv)).reshape(-1))
                if not shap_vals:
                    return []
                scores = np.mean(np.vstack(shap_vals), axis=0)
            else:
                explainer = shap.TreeExplainer(getattr(model, 'model', None))
                sv = explainer.shap_values(X)
                if isinstance(sv, list):
                    sv = sv[1] if len(sv) > 1 else sv[0]
                scores = np.abs(np.asarray(sv)).reshape(-1)

            feats = list(X.columns)
            order = np.argsort(scores)[::-1][:top_n]
            out: List[Dict[str, Any]] = []
            for idx in order:
                feat = feats[int(idx)]
                out.append(
                    {
                        'feature': feat,
                        'importance': float(scores[int(idx)]),
                        'value': float(X.iloc[0][feat]) if pd.notna(X.iloc[0][feat]) else None,
                        'contribution': 'positive' if float(X.iloc[0][feat]) >= 0 else 'negative',
                    }
                )
            return out
        except Exception:
            # Fallback: model feature importance if available
            try:
                imp = model.get_feature_importance()
                if isinstance(imp, pd.DataFrame) and 'feature' in imp.columns:
                    imp = imp.head(top_n)
                    return [
                        {
                            'feature': r['feature'],
                            'importance': float(r.get('importance', r.get('importance_avg', 0.0))),
                            'value': float(X.iloc[0][r['feature']]) if r['feature'] in X.columns else None,
                            'contribution': 'positive',
                        }
                        for r in imp.to_dict(orient='records')
                    ]
            except Exception:
                pass
            return []
    
    def predict_ensemble(
        self,
        ticker: str,
        model_types: List[str] = ['xgboost', 'lightgbm', 'ensemble'],
        as_of_date: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate predictions using multiple models and combine results.
        
        Args:
            ticker: Stock ticker symbol
            model_types: List of model types to use
            as_of_date: Date to generate prediction as of
            
        Returns:
            Dictionary with ensemble prediction results
        """
        predictions = []
        model_results = {}
        
        for model_type in model_types:
            try:
                result = self.predict(ticker, model_type=model_type, as_of_date=as_of_date)
                predictions.append(result)
                model_results[model_type] = result
            except Exception as e:
                logger.error(f"Error getting prediction from {model_type}: {e}")
        
        if not predictions:
            raise ValueError(f"No predictions available for {ticker}")
        
        # Calculate ensemble metrics
        avg_prob_up = np.mean([p['probability_up'] for p in predictions])
        avg_prob_down = np.mean([p['probability_down'] for p in predictions])
        
        # Majority vote
        votes_up = sum(1 for p in predictions if p['prediction'] == 1)
        votes_down = len(predictions) - votes_up
        
        ensemble_prediction = 1 if votes_up > votes_down else 0
        
        # Agreement score (proportion of models that agree)
        agreement = max(votes_up, votes_down) / len(predictions)
        
        result = {
            'ticker': ticker,
            'ensemble_prediction': ensemble_prediction,
            'ensemble_label': 'UP' if ensemble_prediction == 1 else 'DOWN',
            'avg_probability_up': float(avg_prob_up),
            'avg_probability_down': float(avg_prob_down),
            'votes_up': votes_up,
            'votes_down': votes_down,
            'agreement_score': float(agreement),
            'num_models': len(predictions),
            'model_predictions': model_results,
            'prediction_date': datetime.now().isoformat(),
            'as_of_date': as_of_date or datetime.now().date().isoformat()
        }
        
        logger.info(f"{ticker} ensemble: {result['ensemble_label']} "
                   f"(agreement: {agreement:.2%}, {votes_up}/{len(predictions)} models)")
        
        return result
    
    def save_prediction(self, prediction: Dict[str, Any]) -> None:
        """
        Save prediction to database.
        
        Args:
            prediction: Prediction dictionary from predict() or predict_ensemble()
        """
        db = get_db_connection()
        backend_name = get_backend().__class__.__name__

        # Only persist for PostgreSQL schema (DuckDB schema differs across versions in this repo).
        if backend_name != 'PostgreSQLBackend':
            logger.info("Skipping prediction persistence for non-PostgreSQL backend")
            return

        ticker = prediction['ticker']
        prediction_date = pd.to_datetime(prediction.get('as_of_date') or datetime.utcnow().date()).date()
        horizon_days = 5
        target_date = prediction_date + timedelta(days=horizon_days)
        model_name = prediction.get('model_type', 'ensemble')
        predicted_direction = int(prediction.get('prediction', prediction.get('ensemble_prediction', 0)))
        confidence = float(prediction.get('confidence', prediction.get('agreement_score', 0.5)))
        feature_version = 'ohlcv_fe_v1'

        sql = """
        INSERT INTO ml_predictions (
            ticker, prediction_date, target_date, horizon_days, model_name,
            predicted_return, predicted_direction, confidence, feature_version
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (ticker, prediction_date, target_date, model_name)
        DO UPDATE SET
            predicted_direction = EXCLUDED.predicted_direction,
            confidence = EXCLUDED.confidence,
            feature_version = EXCLUDED.feature_version
        """
        db.execute(
            sql,
            (
                ticker,
                prediction_date,
                target_date,
                horizon_days,
                model_name,
                None,
                predicted_direction,
                confidence,
                feature_version,
            ),
        )
    
    def batch_predict(
        self,
        tickers: List[str],
        use_ensemble: bool = True,
        save_to_db: bool = True,
        **kwargs
    ) -> Dict[str, Dict[str, Any]]:
        """
        Generate predictions for multiple tickers.
        
        Args:
            tickers: List of ticker symbols
            use_ensemble: Whether to use ensemble predictions
            save_to_db: Whether to save predictions to database
            **kwargs: Additional arguments for predict/predict_ensemble
            
        Returns:
            Dictionary mapping tickers to prediction results
        """
        results = {}
        
        for ticker in tickers:
            try:
                logger.info(f"Generating prediction for {ticker}")
                
                if use_ensemble:
                    prediction = self.predict_ensemble(ticker, **kwargs)
                else:
                    prediction = self.predict(ticker, **kwargs)
                
                results[ticker] = prediction
                
                if save_to_db:
                    self.save_prediction(prediction)
                    
            except Exception as e:
                logger.error(f"Error predicting {ticker}: {e}")
                results[ticker] = {'error': str(e)}
        
        return results
    
    def get_historical_predictions(
        self,
        ticker: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        prediction_type: Optional[str] = None
    ) -> pd.DataFrame:
        """
        Get historical predictions for a ticker.
        
        Args:
            ticker: Stock ticker symbol
            start_date: Start date filter (YYYY-MM-DD)
            end_date: End date filter (YYYY-MM-DD)
            prediction_type: Filter by prediction type
            
        Returns:
            DataFrame with historical predictions
        """
        db = get_db_connection()

        query = f"""
        SELECT *
        FROM ml_predictions
        WHERE ticker = '{ticker}'
        """

        if start_date:
            query += f" AND prediction_date >= '{start_date}'"
        if end_date:
            query += f" AND prediction_date <= '{end_date}'"
        if prediction_type:
            query += f" AND model_name = '{prediction_type}'"

        query += " ORDER BY prediction_date DESC"
        return db.query(query)
