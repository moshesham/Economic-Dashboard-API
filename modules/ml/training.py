"""
ML Model Training Module

Provides model training functionality with walk-forward validation for time series data.
Includes hyperparameter tuning and comprehensive training pipeline.
"""

import pandas as pd
import numpy as np
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from pathlib import Path
import logging
from sklearn.model_selection import TimeSeriesSplit
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, roc_auc_score
import json

from .models import XGBoostModel, LightGBMModel, EnsembleModel
from .feature_engineering import FeatureEngineer
from modules.database.factory import get_db_connection

logger = logging.getLogger(__name__)


class ModelTrainer:
    """
    Handles ML model training with walk-forward validation for stock predictions.
    
    Features:
    - Walk-forward cross-validation (time series split)
    - Training/validation/test split
    - Hyperparameter tuning
    - Model persistence
    - Training history tracking
    """
    
    def __init__(
        self,
        db_path: str = "data/duckdb/economic_dashboard.duckdb",
        models_dir: str = "data/models"
    ):
        """
        Initialize the model trainer.
        
        Args:
            db_path: Path to DuckDB database
            models_dir: Directory to save trained models
        """
        # Backwards-compat: callers may pass a DuckDB path.
        self.db_path = db_path
        if os.getenv('DATABASE_BACKEND', 'duckdb').lower() == 'duckdb' and not os.getenv('DUCKDB_PATH'):
            os.environ['DUCKDB_PATH'] = db_path
        self.models_dir = Path(models_dir)
        self.models_dir.mkdir(parents=True, exist_ok=True)
        
        self.training_history = []
        
    def prepare_training_data(
        self,
        ticker: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        prediction_horizon: int = 5  # 5 trading days = 1 week
    ) -> Tuple[pd.DataFrame, pd.Series]:
        """
        Prepare training data with features and target variable.
        
        Target: Binary classification (1 if price increases over next week, 0 otherwise)
        
        Args:
            ticker: Stock ticker symbol
            start_date: Start date for training data (YYYY-MM-DD)
            end_date: End date for training data (YYYY-MM-DD)
            prediction_horizon: Number of days ahead to predict
            
        Returns:
            Tuple of (features DataFrame, target Series)
        """
        db = get_db_connection()

        query = f"""
        SELECT date, open, high, low, close, volume, adj_close
        FROM yfinance_ohlcv
        WHERE ticker = '{ticker}'
        """
        if start_date:
            query += f" AND date >= '{start_date}'"
        if end_date:
            query += f" AND date <= '{end_date}'"
        query += " ORDER BY date"

        df = db.query(query)
        if df.empty:
            raise ValueError(f"No OHLCV data found for {ticker} in yfinance_ohlcv")

        df['date'] = pd.to_datetime(df['date'])
        df = df.sort_values('date').set_index('date')

        # Ensure required numeric columns exist
        for col in ['open', 'high', 'low', 'close', 'volume']:
            if col not in df.columns:
                raise ValueError(f"Missing column '{col}' in yfinance_ohlcv for {ticker}")

        df['future_close'] = df['close'].shift(-prediction_horizon)
        df = df.dropna(subset=['future_close'])

        y = (df['future_close'] > df['close']).astype(int)

        # Generate features from OHLCV (works for both DuckDB and PostgreSQL backends)
        ohlcv = df[['open', 'high', 'low', 'close', 'volume']].copy()
        engineer = FeatureEngineer()
        X = engineer.generate_all_features(ohlcv)

        # Basic cleanup: drop rows with any NA in target alignment, then fill remaining NAs in features
        X = X.replace([np.inf, -np.inf], np.nan)
        X = X.loc[y.index]

        # Remove rows where features are entirely missing (early rolling windows)
        valid_mask = X.notna().any(axis=1)
        X = X.loc[valid_mask]
        y = y.loc[valid_mask]

        X = X.fillna(X.median(numeric_only=True))

        logger.info(f"Prepared {len(X)} samples with {X.shape[1]} features for {ticker}")
        logger.info(f"Target distribution: {y.value_counts().to_dict()}")

        return X, y
    
    def walk_forward_validation(
        self,
        X: pd.DataFrame,
        y: pd.Series,
        model_type: str = 'xgboost',
        n_splits: int = 5,
        test_size: float = 0.2,
        **model_params
    ) -> Dict[str, Any]:
        """
        Perform walk-forward cross-validation on time series data.
        
        Args:
            X: Feature matrix
            y: Target vector
            model_type: Type of model ('xgboost', 'lightgbm', 'ensemble')
            n_splits: Number of splits for time series cross-validation
            test_size: Proportion of data to use as final test set
            **model_params: Additional parameters for model initialization
            
        Returns:
            Dictionary containing validation results and trained models
        """
        # Split data into train+validation and test
        split_idx = int(len(X) * (1 - test_size))
        X_train_val, X_test = X.iloc[:split_idx], X.iloc[split_idx:]
        y_train_val, y_test = y.iloc[:split_idx], y.iloc[split_idx:]
        
        # Time series cross-validation
        tscv = TimeSeriesSplit(n_splits=n_splits)
        
        fold_results = []
        models = []
        
        logger.info(f"Starting walk-forward validation with {n_splits} splits")
        
        for fold, (train_idx, val_idx) in enumerate(tscv.split(X_train_val), 1):
            logger.info(f"Training fold {fold}/{n_splits}")
            
            X_train = X_train_val.iloc[train_idx]
            X_val = X_train_val.iloc[val_idx]
            y_train = y_train_val.iloc[train_idx]
            y_val = y_train_val.iloc[val_idx]
            
            # Initialize model
            if model_type == 'xgboost':
                model = XGBoostModel(**model_params)
            elif model_type == 'lightgbm':
                model = LightGBMModel(**model_params)
            elif model_type == 'ensemble':
                model = EnsembleModel(**model_params)
            else:
                raise ValueError(f"Unknown model type: {model_type}")
            
            # Train model
            model.fit(X_train, y_train, eval_set=[(X_val, y_val)])
            
            # Evaluate on validation set
            y_pred = model.predict(X_val)
            y_proba = model.predict_proba(X_val)
            
            metrics = {
                'fold': fold,
                'train_size': len(X_train),
                'val_size': len(X_val),
                'accuracy': accuracy_score(y_val, y_pred),
                'precision': precision_score(y_val, y_pred, zero_division=0),
                'recall': recall_score(y_val, y_pred, zero_division=0),
                'f1': f1_score(y_val, y_pred, zero_division=0),
                'roc_auc': roc_auc_score(y_val, y_proba[:, 1]) if len(np.unique(y_val)) > 1 else 0.0
            }
            
            fold_results.append(metrics)
            models.append(model)
            
            logger.info(f"Fold {fold} - Accuracy: {metrics['accuracy']:.4f}, "
                       f"F1: {metrics['f1']:.4f}, ROC-AUC: {metrics['roc_auc']:.4f}")
        
        # Calculate average validation metrics
        avg_metrics = {
            metric: np.mean([fold[metric] for fold in fold_results])
            for metric in ['accuracy', 'precision', 'recall', 'f1', 'roc_auc']
        }
        
        logger.info(f"Average validation metrics: {avg_metrics}")
        
        # Train final model on all train+val data
        logger.info("Training final model on full training data")
        
        if model_type == 'xgboost':
            final_model = XGBoostModel(**model_params)
        elif model_type == 'lightgbm':
            final_model = LightGBMModel(**model_params)
        elif model_type == 'ensemble':
            final_model = EnsembleModel(**model_params)
        
        final_model.fit(X_train_val, y_train_val)
        
        # Evaluate on test set
        y_test_pred = final_model.predict(X_test)
        y_test_proba = final_model.predict_proba(X_test)
        
        test_metrics = {
            'accuracy': accuracy_score(y_test, y_test_pred),
            'precision': precision_score(y_test, y_test_pred, zero_division=0),
            'recall': recall_score(y_test, y_test_pred, zero_division=0),
            'f1': f1_score(y_test, y_test_pred, zero_division=0),
            'roc_auc': roc_auc_score(y_test, y_test_proba[:, 1]) if len(np.unique(y_test)) > 1 else 0.0
        }
        
        logger.info(f"Test set metrics: {test_metrics}")
        
        return {
            'final_model': final_model,
            'fold_models': models,
            'fold_results': fold_results,
            'avg_validation_metrics': avg_metrics,
            'test_metrics': test_metrics,
            'train_val_size': len(X_train_val),
            'test_size': len(X_test)
        }
    
    def train_model(
        self,
        ticker: str,
        model_type: str = 'ensemble',
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        n_splits: int = 5,
        test_size: float = 0.2,
        save_model: bool = True,
        **model_params
    ) -> Dict[str, Any]:
        """
        Complete training pipeline for a ticker.
        
        Args:
            ticker: Stock ticker symbol
            model_type: Type of model ('xgboost', 'lightgbm', 'ensemble')
            start_date: Start date for training data
            end_date: End date for training data
            n_splits: Number of CV splits
            test_size: Test set proportion
            save_model: Whether to save the trained model
            **model_params: Additional model parameters
            
        Returns:
            Dictionary with training results and model
        """
        logger.info(f"Starting training pipeline for {ticker}")
        
        # Prepare data
        X, y = self.prepare_training_data(ticker, start_date, end_date)
        
        # Perform walk-forward validation
        results = self.walk_forward_validation(
            X, y, model_type, n_splits, test_size, **model_params
        )
        
        # Save model if requested
        if save_model:
            model_path = self.models_dir / f"{ticker}_{model_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pkl"
            results['final_model'].save(str(model_path))
            results['model_path'] = str(model_path)
            logger.info(f"Model saved to {model_path}")
        
        # Record training history
        training_record = {
            'timestamp': datetime.now().isoformat(),
            'ticker': ticker,
            'model_type': model_type,
            'train_val_size': results['train_val_size'],
            'test_size': results['test_size'],
            'n_splits': n_splits,
            'avg_validation_metrics': results['avg_validation_metrics'],
            'test_metrics': results['test_metrics'],
            'model_path': results.get('model_path')
        }
        
        self.training_history.append(training_record)
        
        # Save training history
        history_path = self.models_dir / 'training_history.json'
        with open(history_path, 'w') as f:
            json.dump(self.training_history, f, indent=2)
        
        logger.info(f"Training completed for {ticker}")
        
        return results
    
    def batch_train(
        self,
        tickers: List[str],
        model_type: str = 'ensemble',
        **kwargs
    ) -> Dict[str, Dict[str, Any]]:
        """
        Train models for multiple tickers.
        
        Args:
            tickers: List of ticker symbols
            model_type: Type of model to train
            **kwargs: Additional arguments passed to train_model
            
        Returns:
            Dictionary mapping tickers to their training results
        """
        results = {}
        
        for ticker in tickers:
            try:
                logger.info(f"Training model for {ticker}")
                results[ticker] = self.train_model(ticker, model_type, **kwargs)
            except Exception as e:
                logger.error(f"Error training model for {ticker}: {e}")
                results[ticker] = {'error': str(e)}
        
        return results
    
    def get_best_model_path(self, ticker: str, model_type: str = 'ensemble') -> Optional[str]:
        """
        Get the path to the best saved model for a ticker.
        
        Args:
            ticker: Stock ticker symbol
            model_type: Type of model
            
        Returns:
            Path to best model or None if not found
        """
        pattern = f"{ticker}_{model_type}_*.pkl"
        model_files = list(self.models_dir.glob(pattern))
        
        if not model_files:
            return None
        
        # Return most recent model
        return str(sorted(model_files)[-1])
