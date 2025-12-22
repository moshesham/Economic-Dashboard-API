"""
Model Registry and Versioning System

Centralized model management including:
- Model versioning and tracking
- Performance monitoring
- Model deployment management
- A/B testing support
- Model rollback capabilities
- Metadata and lineage tracking
"""

import json
import pickle
import shutil
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import logging
import pandas as pd

logger = logging.getLogger(__name__)


class ModelStatus(Enum):
    """Model deployment status."""
    TRAINING = "training"
    STAGING = "staging"
    PRODUCTION = "production"
    ARCHIVED = "archived"
    FAILED = "failed"


@dataclass
class ModelMetadata:
    """Metadata for a trained model."""
    
    # Identification
    model_id: str
    model_name: str
    version: str
    ticker: str
    
    # Model details
    model_type: str  # 'xgboost', 'lightgbm', 'ensemble'
    algorithm: str
    
    # Training info
    trained_at: str
    training_duration_seconds: float
    trained_by: str = "system"
    
    # Dataset info
    n_train_samples: int
    n_features: int
    feature_names: List[str]
    target_variable: str
    data_start_date: str
    data_end_date: str
    
    # Performance metrics
    train_metrics: Dict[str, float]
    val_metrics: Dict[str, float]
    test_metrics: Dict[str, float]
    
    # Hyperparameters
    hyperparameters: Dict[str, Any]
    
    # Status
    status: str = ModelStatus.STAGING.value
    
    # Deployment
    deployed_at: Optional[str] = None
    deployment_environment: Optional[str] = None
    
    # Additional metadata
    description: Optional[str] = None
    tags: List[str] = None
    
    # File paths
    model_path: Optional[str] = None
    artifacts_path: Optional[str] = None
    
    def __post_init__(self):
        """Initialize default values."""
        if self.tags is None:
            self.tags = []
    
    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'ModelMetadata':
        """Create from dictionary."""
        return cls(**data)


class ModelRegistry:
    """
    Centralized registry for managing trained models.
    
    Features:
    - Model versioning (semantic versioning)
    - Metadata tracking
    - Performance monitoring
    - Model promotion (staging → production)
    - Model rollback
    - A/B testing support
    - Postgres persistence for model metadata
    """
    
    def __init__(self, registry_dir: str = "data/models/registry", persist_to_db: bool = True):
        """
        Initialize model registry.
        
        Args:
            registry_dir: Directory for registry storage
            persist_to_db: Whether to persist metadata to database (default True)
        """
        self.registry_dir = Path(registry_dir)
        self.registry_dir.mkdir(parents=True, exist_ok=True)
        self.persist_to_db = persist_to_db
        
        # Registry metadata file
        self.metadata_file = self.registry_dir / "registry.json"
        
        # Load or initialize registry
        self.models: Dict[str, ModelMetadata] = self._load_registry()
        
    def _persist_to_database(self, metadata: ModelMetadata) -> None:
        """Persist model metadata to the database model_registry table."""
        if not self.persist_to_db:
            return
        try:
            from modules.database.factory import get_db_connection
            db = get_db_connection()
            
            row = pd.DataFrame([{
                'model_id': metadata.model_id,
                'model_name': metadata.model_name,
                'model_version': metadata.version,
                'model_type': metadata.model_type,
                'ticker': metadata.ticker,
                'artifact_path': metadata.model_path,
                'feature_names': json.dumps(metadata.feature_names),
                'hyperparameters': json.dumps(metadata.hyperparameters),
                'training_metrics': json.dumps(metadata.train_metrics),
                'validation_metrics': json.dumps(metadata.val_metrics),
                'status': metadata.status,
                'trained_at': metadata.trained_at,
                'promoted_at': metadata.deployed_at,
            }])
            
            # Upsert using raw SQL for PostgreSQL
            import os
            if os.getenv('DATABASE_BACKEND', 'duckdb').lower() == 'postgresql':
                for _, r in row.iterrows():
                    db.execute("""
                        INSERT INTO model_registry (model_id, model_name, model_version, model_type, ticker, artifact_path, feature_names, hyperparameters, training_metrics, validation_metrics, status, trained_at, promoted_at)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (model_id) DO UPDATE SET
                            status = EXCLUDED.status,
                            promoted_at = EXCLUDED.promoted_at,
                            validation_metrics = EXCLUDED.validation_metrics
                    """, (
                        r['model_id'], r['model_name'], r['model_version'], r['model_type'],
                        r['ticker'], r['artifact_path'], r['feature_names'], r['hyperparameters'],
                        r['training_metrics'], r['validation_metrics'], r['status'],
                        r['trained_at'], r['promoted_at']
                    ))
            else:
                # DuckDB fallback (simple insert or replace)
                db.insert_df(row, 'model_registry', if_exists='append')
            
            logger.info(f"Persisted model metadata to database: {metadata.model_id}")
        except Exception as e:
            logger.warning(f"Failed to persist model metadata to database: {e}")

    def register_model(
        self,
        model: Any,
        metadata: ModelMetadata,
        artifacts: Optional[Dict[str, Any]] = None,
        promote_to_production: bool = False
    ) -> str:
        """
        Register a new model in the registry.
        
        Args:
            model: Trained model object
            metadata: Model metadata
            artifacts: Additional artifacts (plots, reports, etc.)
            promote_to_production: Whether to promote directly to production
            
        Returns:
            Model ID
        """
        model_id = metadata.model_id
        
        logger.info(f"Registering model: {model_id}")
        
        # Create model directory
        model_dir = self.registry_dir / model_id
        model_dir.mkdir(parents=True, exist_ok=True)
        
        # Save model
        model_path = model_dir / "model.pkl"
        with open(model_path, 'wb') as f:
            pickle.dump(model, f)
        metadata.model_path = str(model_path)
        
        # Save artifacts
        if artifacts:
            artifacts_dir = model_dir / "artifacts"
            artifacts_dir.mkdir(exist_ok=True)
            
            for name, artifact in artifacts.items():
                artifact_path = artifacts_dir / f"{name}.pkl"
                with open(artifact_path, 'wb') as f:
                    pickle.dump(artifact, f)
            
            metadata.artifacts_path = str(artifacts_dir)
        
        # Save metadata
        metadata_path = model_dir / "metadata.json"
        with open(metadata_path, 'w') as f:
            json.dump(metadata.to_dict(), f, indent=2, default=str)
        
        # Add to registry
        self.models[model_id] = metadata
        
        # Persist to database
        self._persist_to_database(metadata)
        
        # Auto-promote if requested
        if promote_to_production:
            self.promote_to_production(model_id)
        
        # Save registry
        self._save_registry()
        
        logger.info(f"Model registered successfully: {model_id}")
        logger.info(f"Status: {metadata.status}")
        
        return model_id
    
    def load_model(self, model_id: str) -> Tuple[Any, ModelMetadata]:
        """
        Load a model from the registry.
        
        Args:
            model_id: Model identifier
            
        Returns:
            Tuple of (model object, metadata)
        """
        if model_id not in self.models:
            raise ValueError(f"Model not found: {model_id}")
        
        metadata = self.models[model_id]
        
        if metadata.model_path is None:
            raise ValueError(f"Model path not set for {model_id}")
        
        with open(metadata.model_path, 'rb') as f:
            model = pickle.load(f)
        
        logger.info(f"Loaded model: {model_id} (status: {metadata.status})")
        
        return model, metadata
    
    def get_production_model(self, ticker: str, model_type: Optional[str] = None) -> Tuple[Any, ModelMetadata]:
        """
        Get the current production model for a ticker.
        
        Args:
            ticker: Stock ticker
            model_type: Optional filter by model type
            
        Returns:
            Tuple of (model object, metadata)
        """
        # Find production models for ticker
        production_models = [
            (mid, meta) for mid, meta in self.models.items()
            if meta.status == ModelStatus.PRODUCTION.value
            and meta.ticker == ticker
            and (model_type is None or meta.model_type == model_type)
        ]
        
        if not production_models:
            raise ValueError(f"No production model found for {ticker}")
        
        # If multiple, get most recent
        production_models.sort(key=lambda x: x[1].trained_at, reverse=True)
        model_id, metadata = production_models[0]
        
        return self.load_model(model_id)
    
    def promote_to_production(
        self,
        model_id: str,
        demote_current: bool = True
    ) -> None:
        """
        Promote a model to production.
        
        Args:
            model_id: Model to promote
            demote_current: Whether to demote current production models
        """
        if model_id not in self.models:
            raise ValueError(f"Model not found: {model_id}")
        
        metadata = self.models[model_id]
        ticker = metadata.ticker
        model_type = metadata.model_type
        
        # Demote current production models
        if demote_current:
            for mid, meta in self.models.items():
                if (meta.status == ModelStatus.PRODUCTION.value and
                    meta.ticker == ticker and
                    meta.model_type == model_type):
                    meta.status = ModelStatus.ARCHIVED.value
                    self._persist_to_database(meta)
                    logger.info(f"Demoted model to archived: {mid}")
        
        # Promote new model
        metadata.status = ModelStatus.PRODUCTION.value
        metadata.deployed_at = datetime.now().isoformat()
        metadata.deployment_environment = "production"
        
        self._persist_to_database(metadata)
        self._save_registry()
        
        logger.info(f"Promoted model to production: {model_id}")
    
    def rollback_to_version(self, ticker: str, version: str) -> str:
        """
        Rollback to a previous model version.
        
        Args:
            ticker: Stock ticker
            version: Version to rollback to
            
        Returns:
            Model ID of rolled-back model
        """
        # Find model with specified version
        candidates = [
            (mid, meta) for mid, meta in self.models.items()
            if meta.ticker == ticker and meta.version == version
        ]
        
        if not candidates:
            raise ValueError(f"No model found for {ticker} version {version}")
        
        model_id = candidates[0][0]
        
        # Promote to production
        self.promote_to_production(model_id)
        
        logger.info(f"Rolled back {ticker} to version {version} (model_id: {model_id})")
        
        return model_id
    
    def compare_models(
        self,
        model_ids: List[str],
        metric: str = 'test_metrics.f1'
    ) -> pd.DataFrame:
        """
        Compare multiple models.
        
        Args:
            model_ids: List of model IDs to compare
            metric: Metric path to compare (e.g., 'test_metrics.f1')
            
        Returns:
            DataFrame with comparison results
        """
        comparison = []
        
        for model_id in model_ids:
            if model_id not in self.models:
                logger.warning(f"Model not found: {model_id}")
                continue
            
            meta = self.models[model_id]
            
            # Extract metric value
            metric_parts = metric.split('.')
            value = meta.to_dict()
            for part in metric_parts:
                value = value.get(part, None)
                if value is None:
                    break
            
            comparison.append({
                'model_id': model_id,
                'version': meta.version,
                'model_type': meta.model_type,
                'status': meta.status,
                'trained_at': meta.trained_at,
                metric: value,
                'n_train_samples': meta.n_train_samples,
                'n_features': meta.n_features
            })
        
        df = pd.DataFrame(comparison)
        
        if not df.empty and metric in df.columns:
            df = df.sort_values(metric, ascending=False)
        
        return df
    
    def get_model_history(
        self,
        ticker: str,
        model_type: Optional[str] = None
    ) -> pd.DataFrame:
        """
        Get training history for a ticker.
        
        Args:
            ticker: Stock ticker
            model_type: Optional filter by model type
            
        Returns:
            DataFrame with model history
        """
        history = []
        
        for model_id, meta in self.models.items():
            if meta.ticker != ticker:
                continue
            
            if model_type and meta.model_type != model_type:
                continue
            
            history.append({
                'model_id': model_id,
                'version': meta.version,
                'model_type': meta.model_type,
                'trained_at': meta.trained_at,
                'status': meta.status,
                'train_f1': meta.train_metrics.get('f1', None),
                'val_f1': meta.val_metrics.get('f1', None),
                'test_f1': meta.test_metrics.get('f1', None),
                'n_train_samples': meta.n_train_samples,
                'n_features': meta.n_features
            })
        
        df = pd.DataFrame(history)
        
        if not df.empty:
            df = df.sort_values('trained_at', ascending=False)
        
        return df
    
    def delete_model(self, model_id: str, confirm: bool = False) -> None:
        """
        Delete a model from the registry.
        
        Args:
            model_id: Model to delete
            confirm: Confirmation flag (safety check)
        """
        if not confirm:
            raise ValueError("Must set confirm=True to delete model")
        
        if model_id not in self.models:
            raise ValueError(f"Model not found: {model_id}")
        
        metadata = self.models[model_id]
        
        # Don't allow deleting production models
        if metadata.status == ModelStatus.PRODUCTION.value:
            raise ValueError("Cannot delete production model. Demote first.")
        
        # Delete model directory
        model_dir = self.registry_dir / model_id
        if model_dir.exists():
            shutil.rmtree(model_dir)
        
        # Remove from registry
        del self.models[model_id]
        
        self._save_registry()
        
        logger.info(f"Deleted model: {model_id}")
    
    def update_metadata(
        self,
        model_id: str,
        updates: Dict[str, Any]
    ) -> None:
        """
        Update model metadata.
        
        Args:
            model_id: Model to update
            updates: Dictionary of fields to update
        """
        if model_id not in self.models:
            raise ValueError(f"Model not found: {model_id}")
        
        metadata = self.models[model_id]
        
        # Update metadata
        for key, value in updates.items():
            if hasattr(metadata, key):
                setattr(metadata, key, value)
        
        # Save updated metadata
        model_dir = self.registry_dir / model_id
        metadata_path = model_dir / "metadata.json"
        with open(metadata_path, 'w') as f:
            json.dump(metadata.to_dict(), f, indent=2, default=str)
        
        self._save_registry()
        
        logger.info(f"Updated metadata for model: {model_id}")
    
    def list_models(
        self,
        ticker: Optional[str] = None,
        status: Optional[str] = None,
        model_type: Optional[str] = None
    ) -> List[str]:
        """
        List models matching filters.
        
        Args:
            ticker: Filter by ticker
            status: Filter by status
            model_type: Filter by model type
            
        Returns:
            List of model IDs
        """
        models = []
        
        for model_id, meta in self.models.items():
            if ticker and meta.ticker != ticker:
                continue
            if status and meta.status != status:
                continue
            if model_type and meta.model_type != model_type:
                continue
            
            models.append(model_id)
        
        return models
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get registry statistics."""
        stats = {
            'total_models': len(self.models),
            'by_status': {},
            'by_model_type': {},
            'by_ticker': {},
            'production_models': 0
        }
        
        for meta in self.models.values():
            # Count by status
            stats['by_status'][meta.status] = stats['by_status'].get(meta.status, 0) + 1
            
            # Count by model type
            stats['by_model_type'][meta.model_type] = stats['by_model_type'].get(meta.model_type, 0) + 1
            
            # Count by ticker
            stats['by_ticker'][meta.ticker] = stats['by_ticker'].get(meta.ticker, 0) + 1
            
            # Count production
            if meta.status == ModelStatus.PRODUCTION.value:
                stats['production_models'] += 1
        
        return stats
    
    def _load_registry(self) -> Dict[str, ModelMetadata]:
        """Load registry from disk."""
        if not self.metadata_file.exists():
            return {}
        
        with open(self.metadata_file, 'r') as f:
            data = json.load(f)
        
        models = {
            model_id: ModelMetadata.from_dict(meta_dict)
            for model_id, meta_dict in data.items()
        }
        
        logger.info(f"Loaded {len(models)} models from registry")
        
        return models
    
    def _save_registry(self) -> None:
        """Save registry to disk."""
        data = {
            model_id: meta.to_dict()
            for model_id, meta in self.models.items()
        }
        
        with open(self.metadata_file, 'w') as f:
            json.dump(data, f, indent=2, default=str)
    
    def export_registry(self, export_path: str) -> None:
        """
        Export registry to a backup file.
        
        Args:
            export_path: Path to export file
        """
        data = {
            'exported_at': datetime.now().isoformat(),
            'registry': {
                model_id: meta.to_dict()
                for model_id, meta in self.models.items()
            }
        }
        
        with open(export_path, 'w') as f:
            json.dump(data, f, indent=2, default=str)
        
        logger.info(f"Registry exported to {export_path}")


def generate_model_id(ticker: str, model_type: str, version: str) -> str:
    """
    Generate a unique model ID.
    
    Args:
        ticker: Stock ticker
        model_type: Model type
        version: Model version
        
    Returns:
        Model ID string
    """
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    return f"{ticker}_{model_type}_v{version}_{timestamp}"


def generate_version(major: int = 1, minor: int = 0, patch: int = 0) -> str:
    """
    Generate semantic version string.
    
    Args:
        major: Major version
        minor: Minor version
        patch: Patch version
        
    Returns:
        Version string (e.g., "1.0.0")
    """
    return f"{major}.{minor}.{patch}"
