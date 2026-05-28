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

try:
    from .models import XGBoostModel, LightGBMModel, EnsembleModel
    from .training import ModelTrainer
    from .prediction import PredictionEngine
    from .evaluation import ModelEvaluator
    from .feature_engineering import FeatureEngineer, FeatureConfig
    from .hyperparameter_tuning import HyperparameterOptimizer, OptimizationConfig, optimize_model_hyperparameters
except ImportError:
    # ML dependencies (xgboost, lightgbm, sklearn) not installed in this environment
    XGBoostModel = LightGBMModel = EnsembleModel = None
    ModelTrainer = PredictionEngine = ModelEvaluator = None
    FeatureEngineer = FeatureConfig = None
    HyperparameterOptimizer = OptimizationConfig = optimize_model_hyperparameters = None

from .recession_model import RecessionProbabilityModel

__all__ = [
    # Core Models
    'XGBoostModel',
    'LightGBMModel',
    'EnsembleModel',
    
    # Training & Prediction
    'ModelTrainer',
    'PredictionEngine',
    
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
