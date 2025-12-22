"""
ML models module for stock prediction and economic forecasting.

Comprehensive machine learning toolkit including:
- Models: XGBoost, LightGBM, Ensemble models
- Training: Walk-forward validation, hyperparameter tuning
- Prediction: Multi-horizon forecasts, confidence scoring
- Evaluation: Financial metrics, model performance tracking
- Feature Engineering: 100+ technical, fundamental, and alternative features
- Hyperparameter Optimization: Bayesian optimization with Optuna
- Recession Modeling: Economic indicator-based probability models
"""

from .models import XGBoostModel, LightGBMModel, EnsembleModel
from .training import ModelTrainer
from .prediction import PredictionEngine
from .evaluation import ModelEvaluator
from .prediction_engine import PredictionEngine as AdvancedPredictionEngine
from .recession_model import RecessionProbabilityModel
from .feature_engineering import FeatureEngineer, FeatureConfig
from .hyperparameter_tuning import HyperparameterOptimizer, OptimizationConfig, optimize_model_hyperparameters

__all__ = [
    # Core Models
    'XGBoostModel',
    'LightGBMModel',
    'EnsembleModel',
    
    # Training & Prediction
    'ModelTrainer',
    'PredictionEngine',
    'AdvancedPredictionEngine',
    
    # Evaluation
    'ModelEvaluator',
    
    # Feature Engineering
    'FeatureEngineer',
    'FeatureConfig',
    
    # Hyperparameter Optimization
    'HyperparameterOptimizer',
    'OptimizationConfig',
    'optimize_model_hyperparameters',
    
    # Specialized Models
    'RecessionProbabilityModel',
]

__version__ = '2.0.0'
