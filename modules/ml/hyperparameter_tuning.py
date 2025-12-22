"""
Hyperparameter Optimization Module

Advanced hyperparameter tuning using:
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple, Any, Callable
from dataclasses import dataclass
import logging
from datetime import datetime
from pathlib import Path
import json

logger = logging.getLogger(__name__)

# Lazy imports for optional dependencies
try:
    import optuna
    from optuna.pruners import MedianPruner
    from optuna.samplers import TPESampler
    OPTUNA_AVAILABLE = True
except ImportError:
    OPTUNA_AVAILABLE = False
    logger.warning("Optuna not available. Install with: pip install optuna")

from sklearn.model_selection import TimeSeriesSplit
from sklearn.metrics import accuracy_score, f1_score, roc_auc_score


@dataclass
class OptimizationConfig:
    """Configuration for hyperparameter optimization."""
    
    # Optimization settings
    n_trials: int = 100
    timeout_seconds: Optional[int] = 3600  # 1 hour
    n_jobs: int = -1  # Parallel trials
    
    # Validation settings
    n_cv_splits: int = 5
    test_size: float = 0.2
    
    # Objective settings
    optimize_for: str = 'f1'  # 'accuracy', 'f1', 'roc_auc', 'multi'
    stability_weight: float = 0.2  # For multi-objective
    
    # Early stopping
    early_stopping_patience: int = 20
    pruning_enabled: bool = True
    
    # Feature selection
    feature_selection_enabled: bool = True
    min_features_pct: float = 0.3  # Minimum 30% of features
    
    # Model specific
    model_type: str = 'xgboost'  # 'xgboost', 'lightgbm', 'ensemble'


class HyperparameterOptimizer:
    """
    Advanced hyperparameter optimization for ML models.
    
    Features:
    - Bayesian optimization with Optuna
    - Walk-forward time-series validation
    - Multi-objective optimization
    - Automated feature selection
    - Results tracking and visualization
    """
    
    def __init__(
        self,
        config: Optional[OptimizationConfig] = None,
        results_dir: str = "data/optimization"
    ):
        """
        Initialize hyperparameter optimizer.
        
        Args:
            config: Optimization configuration
            results_dir: Directory to save optimization results
        """
        if not OPTUNA_AVAILABLE:
            raise ImportError("Optuna is required for hyperparameter optimization")
        
        self.config = config or OptimizationConfig()
        self.results_dir = Path(results_dir)
        self.results_dir.mkdir(parents=True, exist_ok=True)
        
        self.study: Optional[optuna.Study] = None
        self.best_params: Optional[Dict] = None
        self.optimization_history: List[Dict] = []
        
    def optimize(
        self,
        X: pd.DataFrame,
        y: pd.Series,
        study_name: Optional[str] = None,
        load_if_exists: bool = False
    ) -> Dict[str, Any]:
        """
        Run hyperparameter optimization.
        
        Args:
            X: Feature matrix
            y: Target vector
            study_name: Name for the study (for persistence)
            load_if_exists: Whether to load existing study
            
        Returns:
            Dictionary with best parameters and optimization results
        """
        logger.info(f"Starting hyperparameter optimization for {self.config.model_type}")
        logger.info(f"Dataset: {len(X)} samples, {len(X.columns)} features")
        
        # Create study
        study_name = study_name or f"{self.config.model_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Setup storage (SQLite for persistence)
        storage_path = self.results_dir / "optuna_studies.db"
        storage = f"sqlite:///{storage_path}"
        
        # Create or load study
        sampler = TPESampler(seed=42)
        pruner = MedianPruner() if self.config.pruning_enabled else None
        
        self.study = optuna.create_study(
            study_name=study_name,
            direction='maximize',  # Maximize objective metric
            sampler=sampler,
            pruner=pruner,
            storage=storage,
            load_if_exists=load_if_exists
        )
        
        # Define objective function
        objective = self._create_objective_function(X, y)
        
        # Run optimization
        self.study.optimize(
            objective,
            n_trials=self.config.n_trials,
            timeout=self.config.timeout_seconds,
            n_jobs=self.config.n_jobs,
            show_progress_bar=True,
            callbacks=[self._optimization_callback]
        )
        
        # Get best parameters
        self.best_params = self.study.best_params
        
        logger.info(f"Optimization completed: {len(self.study.trials)} trials")
        logger.info(f"Best {self.config.optimize_for}: {self.study.best_value:.4f}")
        logger.info(f"Best parameters: {self.best_params}")
        
        # Save results
        results = self._compile_results(X, y)
        self._save_results(results, study_name)
        
        return results
    
    def _create_objective_function(
        self,
        X: pd.DataFrame,
        y: pd.Series
    ) -> Callable:
        """Create objective function for Optuna."""
        
        def objective(trial: optuna.Trial) -> float:
            """
            Objective function to minimize/maximize.
            
            Args:
                trial: Optuna trial object
                
            Returns:
                Objective value (higher is better)
            """
            # Suggest hyperparameters based on model type
            params = self._suggest_parameters(trial)
            
            # Feature selection
            if self.config.feature_selection_enabled:
                selected_features = self._suggest_features(trial, X)
                X_trial = X[selected_features]
            else:
                X_trial = X
            
            # Time-series cross-validation
            scores = self._evaluate_with_cv(X_trial, y, params, trial)
            
            if not scores:
                return 0.0
            
            # Calculate objective based on configuration
            if self.config.optimize_for == 'multi':
                # Multi-objective: balance mean and stability
                mean_score = np.mean(scores)
                std_score = np.std(scores)
                
                # Higher mean, lower std is better
                objective_value = (
                    mean_score * (1 - self.config.stability_weight) -
                    std_score * self.config.stability_weight
                )
            else:
                # Single objective: maximize mean score
                objective_value = np.mean(scores)
            
            # Report intermediate value for pruning
            trial.set_user_attr('cv_scores', scores)
            trial.set_user_attr('cv_mean', np.mean(scores))
            trial.set_user_attr('cv_std', np.std(scores))
            
            return objective_value
        
        return objective
    
    def _suggest_parameters(self, trial: optuna.Trial) -> Dict[str, Any]:
        """Suggest hyperparameters based on model type."""
        
        if self.config.model_type == 'xgboost':
            return {
                'n_estimators': trial.suggest_int('n_estimators', 100, 1000, step=50),
                'max_depth': trial.suggest_int('max_depth', 3, 10),
                'learning_rate': trial.suggest_float('learning_rate', 0.01, 0.3, log=True),
                'subsample': trial.suggest_float('subsample', 0.5, 1.0),
                'colsample_bytree': trial.suggest_float('colsample_bytree', 0.5, 1.0),
                'min_child_weight': trial.suggest_int('min_child_weight', 1, 10),
                'gamma': trial.suggest_float('gamma', 0.0, 1.0),
                'reg_alpha': trial.suggest_float('reg_alpha', 0.0, 1.0),
                'reg_lambda': trial.suggest_float('reg_lambda', 0.0, 1.0),
            }
        
        elif self.config.model_type == 'lightgbm':
            return {
                'n_estimators': trial.suggest_int('n_estimators', 100, 1000, step=50),
                'max_depth': trial.suggest_int('max_depth', 3, 10),
                'learning_rate': trial.suggest_float('learning_rate', 0.01, 0.3, log=True),
                'num_leaves': trial.suggest_int('num_leaves', 20, 150),
                'feature_fraction': trial.suggest_float('feature_fraction', 0.5, 1.0),
                'bagging_fraction': trial.suggest_float('bagging_fraction', 0.5, 1.0),
                'bagging_freq': trial.suggest_int('bagging_freq', 1, 7),
                'min_child_samples': trial.suggest_int('min_child_samples', 5, 100),
                'reg_alpha': trial.suggest_float('reg_alpha', 0.0, 1.0),
                'reg_lambda': trial.suggest_float('reg_lambda', 0.0, 1.0),
            }
        
        else:
            raise ValueError(f"Unknown model type: {self.config.model_type}")
    
    def _suggest_features(
        self,
        trial: optuna.Trial,
        X: pd.DataFrame
    ) -> List[str]:
        """
        Suggest subset of features for automated feature selection.
        
        Args:
            trial: Optuna trial
            X: Feature matrix
            
        Returns:
            List of selected feature names
        """
        feature_cols = X.columns.tolist()
        n_features = len(feature_cols)
        min_features = max(int(n_features * self.config.min_features_pct), 5)
        
        # Suggest number of features
        n_selected = trial.suggest_int('n_features', min_features, n_features)
        
        # Suggest which features (using categorical selection)
        # Note: For large feature sets, use importance-based pre-filtering
        selected = []
        for i in range(n_selected):
            if len(feature_cols) > 0:
                feat = trial.suggest_categorical(f'feature_{i}', feature_cols)
                selected.append(feat)
                feature_cols.remove(feat)  # Prevent duplicates
        
        return selected
    
    def _evaluate_with_cv(
        self,
        X: pd.DataFrame,
        y: pd.Series,
        params: Dict[str, Any],
        trial: Optional[optuna.Trial] = None
    ) -> List[float]:
        """
        Evaluate model with time-series cross-validation.
        
        Args:
            X: Feature matrix
            y: Target vector
            params: Model hyperparameters
            trial: Optuna trial for pruning
            
        Returns:
            List of CV fold scores
        """
        tscv = TimeSeriesSplit(n_splits=self.config.n_cv_splits)
        scores = []
        
        for fold, (train_idx, val_idx) in enumerate(tscv.split(X)):
            X_train, X_val = X.iloc[train_idx], X.iloc[val_idx]
            y_train, y_val = y.iloc[train_idx], y.iloc[val_idx]
            
            # Train model
            model = self._create_model(params)
            
            try:
                model.fit(X_train, y_train)
                
                # Predict
                y_pred = model.predict(X_val)
                
                # Calculate score
                if self.config.optimize_for == 'accuracy':
                    score = accuracy_score(y_val, y_pred)
                elif self.config.optimize_for == 'f1':
                    score = f1_score(y_val, y_pred, zero_division=0)
                elif self.config.optimize_for == 'roc_auc':
                    y_proba = model.predict_proba(X_val)[:, 1]
                    score = roc_auc_score(y_val, y_proba)
                else:  # multi
                    score = f1_score(y_val, y_pred, zero_division=0)
                
                scores.append(score)
                
                # Pruning: report intermediate value
                if trial is not None and self.config.pruning_enabled:
                    trial.report(np.mean(scores), fold)
                    
                    # Check if trial should be pruned
                    if trial.should_prune():
                        raise optuna.TrialPruned()
                
            except Exception as e:
                logger.warning(f"Fold {fold} failed: {e}")
                continue
        
        return scores
    
    def _create_model(self, params: Dict[str, Any]):
        """Create model instance with given parameters."""
        if self.config.model_type == 'xgboost':
            import xgboost as xgb
            return xgb.XGBClassifier(
                **params,
                objective='binary:logistic',
                eval_metric='logloss',
                random_state=42,
                n_jobs=1  # Don't nest parallelism
            )
        
        elif self.config.model_type == 'lightgbm':
            import lightgbm as lgb
            return lgb.LGBMClassifier(
                **params,
                objective='binary',
                metric='binary_logloss',
                random_state=42,
                n_jobs=1,
                verbose=-1
            )
        
        else:
            raise ValueError(f"Unknown model type: {self.config.model_type}")
    
    def _optimization_callback(
        self,
        study: optuna.Study,
        trial: optuna.Trial
    ) -> None:
        """Callback for each trial completion."""
        if trial.state == optuna.trial.TrialState.COMPLETE:
            logger.info(
                f"Trial {trial.number}: "
                f"value={trial.value:.4f}, "
                f"params={trial.params}"
            )
            
            # Track history
            self.optimization_history.append({
                'trial': trial.number,
                'value': trial.value,
                'params': trial.params,
                'datetime': trial.datetime_complete.isoformat() if trial.datetime_complete else None
            })
    
    def _compile_results(self, X: pd.DataFrame, y: pd.Series) -> Dict[str, Any]:
        """Compile optimization results."""
        results = {
            'study_name': self.study.study_name,
            'best_params': self.best_params,
            'best_value': self.study.best_value,
            'n_trials': len(self.study.trials),
            'optimization_time': sum(
                (t.duration.total_seconds() if t.duration else 0)
                for t in self.study.trials
            ),
            'config': {
                'model_type': self.config.model_type,
                'n_cv_splits': self.config.n_cv_splits,
                'optimize_for': self.config.optimize_for,
                'feature_selection': self.config.feature_selection_enabled
            },
            'dataset': {
                'n_samples': len(X),
                'n_features': len(X.columns),
                'target_distribution': y.value_counts().to_dict()
            },
            'best_trial': {
                'number': self.study.best_trial.number,
                'value': self.study.best_trial.value,
                'params': self.study.best_trial.params,
                'user_attrs': self.study.best_trial.user_attrs
            },
            'trials_summary': self._summarize_trials(),
            'timestamp': datetime.now().isoformat()
        }
        
        return results
    
    def _summarize_trials(self) -> Dict[str, Any]:
        """Summarize all trials."""
        completed_trials = [
            t for t in self.study.trials
            if t.state == optuna.trial.TrialState.COMPLETE
        ]
        
        if not completed_trials:
            return {}
        
        values = [t.value for t in completed_trials]
        
        return {
            'n_completed': len(completed_trials),
            'n_pruned': len([
                t for t in self.study.trials
                if t.state == optuna.trial.TrialState.PRUNED
            ]),
            'n_failed': len([
                t for t in self.study.trials
                if t.state == optuna.trial.TrialState.FAIL
            ]),
            'value_mean': float(np.mean(values)),
            'value_std': float(np.std(values)),
            'value_min': float(np.min(values)),
            'value_max': float(np.max(values)),
            'value_median': float(np.median(values))
        }
    
    def _save_results(self, results: Dict[str, Any], study_name: str) -> None:
        """Save optimization results to disk."""
        results_path = self.results_dir / f"{study_name}_results.json"
        
        with open(results_path, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        
        logger.info(f"Results saved to {results_path}")
    
    def plot_optimization_history(
        self,
        save_path: Optional[str] = None
    ) -> None:
        """Plot optimization history."""
        try:
            import matplotlib.pyplot as plt
            
            if self.study is None:
                logger.warning("No study available to plot")
                return
            
            fig, axes = plt.subplots(2, 2, figsize=(15, 10))
            
            # Plot 1: Optimization history
            trials = [t.number for t in self.study.trials if t.state == optuna.trial.TrialState.COMPLETE]
            values = [t.value for t in self.study.trials if t.state == optuna.trial.TrialState.COMPLETE]
            
            axes[0, 0].plot(trials, values, marker='o', alpha=0.6)
            axes[0, 0].set_xlabel('Trial')
            axes[0, 0].set_ylabel('Objective Value')
            axes[0, 0].set_title('Optimization History')
            axes[0, 0].grid(True, alpha=0.3)
            
            # Plot 2: Parameter importance
            try:
                importance = optuna.importance.get_param_importances(self.study)
                params = list(importance.keys())[:10]  # Top 10
                importances = [importance[p] for p in params]
                
                axes[0, 1].barh(params, importances)
                axes[0, 1].set_xlabel('Importance')
                axes[0, 1].set_title('Parameter Importance (Top 10)')
                axes[0, 1].grid(True, alpha=0.3, axis='x')
            except Exception as e:
                logger.warning(f"Could not plot parameter importance: {e}")
                axes[0, 1].text(0.5, 0.5, 'Parameter importance\nnot available',
                              ha='center', va='center')
            
            # Plot 3: Parallel coordinate plot for top parameters
            try:
                from optuna.visualization.matplotlib import plot_parallel_coordinate
                
                # Get top parameters by importance
                importance = optuna.importance.get_param_importances(self.study)
                top_params = list(importance.keys())[:5]
                
                plot_parallel_coordinate(self.study, params=top_params, target_name='Objective')
                axes[1, 0].set_title('Parameter Relationships (Top 5)')
            except Exception as e:
                logger.warning(f"Could not plot parallel coordinates: {e}")
                axes[1, 0].text(0.5, 0.5, 'Parallel coordinates\nnot available',
                              ha='center', va='center')
            
            # Plot 4: Distribution of objective values
            axes[1, 1].hist(values, bins=30, edgecolor='black', alpha=0.7)
            axes[1, 1].axvline(self.study.best_value, color='r', linestyle='--',
                             label=f'Best: {self.study.best_value:.4f}')
            axes[1, 1].set_xlabel('Objective Value')
            axes[1, 1].set_ylabel('Frequency')
            axes[1, 1].set_title('Objective Value Distribution')
            axes[1, 1].legend()
            axes[1, 1].grid(True, alpha=0.3)
            
            plt.tight_layout()
            
            if save_path:
                plt.savefig(save_path, dpi=300, bbox_inches='tight')
                logger.info(f"Optimization plots saved to {save_path}")
            else:
                plt.show()
            
            plt.close()
            
        except ImportError:
            logger.warning("Matplotlib not available for plotting")
        except Exception as e:
            logger.error(f"Error creating plots: {e}")
    
    def get_feature_importance_from_optimization(self) -> Optional[pd.DataFrame]:
        """
        Get feature importance from optimization if feature selection was used.
        
        Returns:
            DataFrame with feature selection frequency across trials
        """
        if not self.config.feature_selection_enabled or self.study is None:
            return None
        
        # Count how often each feature was selected
        feature_counts = {}
        total_trials = 0
        
        for trial in self.study.trials:
            if trial.state != optuna.trial.TrialState.COMPLETE:
                continue
            
            total_trials += 1
            
            # Get selected features from params
            selected_features = [
                v for k, v in trial.params.items()
                if k.startswith('feature_')
            ]
            
            for feat in selected_features:
                feature_counts[feat] = feature_counts.get(feat, 0) + 1
        
        if not feature_counts:
            return None
        
        # Create DataFrame
        importance_df = pd.DataFrame([
            {
                'feature': feat,
                'selection_count': count,
                'selection_frequency': count / total_trials
            }
            for feat, count in feature_counts.items()
        ])
        
        importance_df = importance_df.sort_values('selection_frequency', ascending=False)
        
        return importance_df


def optimize_model_hyperparameters(
    X: pd.DataFrame,
    y: pd.Series,
    model_type: str = 'xgboost',
    n_trials: int = 100,
    optimize_for: str = 'f1',
    feature_selection: bool = True,
    results_dir: str = "data/optimization"
) -> Dict[str, Any]:
    """
    Convenience function for hyperparameter optimization.
    
    Args:
        X: Feature matrix
        y: Target vector
        model_type: Type of model ('xgboost', 'lightgbm')
        n_trials: Number of optimization trials
        optimize_for: Metric to optimize ('accuracy', 'f1', 'roc_auc', 'multi')
        feature_selection: Enable automated feature selection
        results_dir: Directory to save results
        
    Returns:
        Dictionary with optimization results
    """
    config = OptimizationConfig(
        n_trials=n_trials,
        model_type=model_type,
        optimize_for=optimize_for,
        feature_selection_enabled=feature_selection
    )
    
    optimizer = HyperparameterOptimizer(config=config, results_dir=results_dir)
    
    results = optimizer.optimize(X, y)
    
    # Generate plots
    plot_path = Path(results_dir) / f"{optimizer.study.study_name}_plots.png"
    optimizer.plot_optimization_history(str(plot_path))
    
    return results
