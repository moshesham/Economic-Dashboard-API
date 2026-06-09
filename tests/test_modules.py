"""Smoke tests for database and feature/ML modules.

These checks are intentionally lightweight and pytest-safe:
- no import-time side effects
- no sys.exit calls during collection
- no dependency on seeded market/options data
"""

import pandas as pd


def test_database_connection_smoke():
    from modules.database import get_db_connection

    db = get_db_connection()
    result = db.query("SELECT 1 AS value")

    assert not result.empty
    assert int(result.iloc[0]["value"]) == 1


def test_feature_calculators_initialize():
    from modules.features.technical_indicators import TechnicalIndicatorCalculator
    from modules.features.options_metrics import OptionsMetricsCalculator
    from modules.features.derived_features import DerivedFeaturesCalculator

    assert TechnicalIndicatorCalculator() is not None
    assert OptionsMetricsCalculator() is not None
    assert DerivedFeaturesCalculator() is not None


def test_ml_models_initialize_and_predict():
    import numpy as np
    from modules.ml.models import XGBoostModel, LightGBMModel, EnsembleModel

    xgb_model = XGBoostModel(n_estimators=10, max_depth=3)
    lgbm_model = LightGBMModel(n_estimators=10, num_leaves=15)
    ensemble_model = EnsembleModel()

    assert xgb_model is not None
    assert lgbm_model is not None
    assert ensemble_model is not None

    features = pd.DataFrame(
        np.random.randn(20, 5),
        columns=[f"feature_{index}" for index in range(5)],
    )
    target = pd.Series(np.random.randint(0, 2, len(features)))

    xgb_model.fit(features, target, verbose=False)
    predictions = xgb_model.predict(features.iloc[:5])
    probabilities = xgb_model.predict_proba(features.iloc[:5])

    assert len(predictions) == 5
    assert probabilities.shape[0] == 5
