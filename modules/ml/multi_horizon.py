"""
Multi-horizon prediction wrapper.

This module reuses the existing PredictionEngine to provide a stable
1d / 5d / 20d response shape while the project only has one trained
model family available locally.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional

from .prediction import PredictionEngine


@dataclass(frozen=True)
class HorizonProfile:
    horizon: str
    horizon_days: int
    confidence_decay: float


class MultiHorizonPredictor:
    """Generate consistent horizon-scoped predictions."""

    def __init__(self, engine: Optional[PredictionEngine] = None):
        self.engine = engine or PredictionEngine()

    def _profile(self, horizon: str) -> HorizonProfile:
        profiles = {
            "1d": HorizonProfile("1d", 1, 1.00),
            "5d": HorizonProfile("5d", 5, 0.95),
            "20d": HorizonProfile("20d", 20, 0.88),
        }
        if horizon not in profiles:
            raise ValueError(f"Unsupported horizon: {horizon}")
        return profiles[horizon]

    def _build_horizon_payload(self, base_prediction: Dict[str, Any], profile: HorizonProfile) -> Dict[str, Any]:
        confidence = float(base_prediction.get("confidence", 0.5)) * profile.confidence_decay
        confidence = max(0.0, min(0.99, confidence))

        probability_up = float(base_prediction.get("probability_up", base_prediction.get("probability", 0.5)))
        probability_down = float(base_prediction.get("probability_down", 1.0 - probability_up))

        return {
            "horizon": profile.horizon,
            "horizon_days": profile.horizon_days,
            "direction": base_prediction.get("prediction_label", "UP" if base_prediction.get("prediction", 1) == 1 else "DOWN"),
            "confidence": confidence,
            "probability_up": probability_up,
            "probability_down": probability_down,
            "model_type": base_prediction.get("model_type", "ensemble"),
            "model_version": base_prediction.get("model_version", base_prediction.get("model_type", "ensemble")),
            "target_date": base_prediction.get("target_date"),
            "prediction_date": base_prediction.get("prediction_date"),
            "source_model": base_prediction.get("model_path"),
        }

    def predict_horizon(
        self,
        ticker: str,
        horizon: str,
        model_type: str = "ensemble",
        include_explanation: bool = False,
        store_result: bool = False,
    ) -> Dict[str, Any]:
        profile = self._profile(horizon)
        base_prediction = self.engine.predict(
            ticker=ticker,
            model_type=model_type,
            store_result=store_result,
            horizon_days=profile.horizon_days,
        )

        payload = self._build_horizon_payload(base_prediction, profile)
        if include_explanation:
            payload["explanation"] = self.engine.explain_prediction(ticker, model_type=model_type)
        return payload

    def predict_all_horizons(
        self,
        ticker: str,
        model_type: str = "ensemble",
        include_explanation: bool = False,
        store_result: bool = False,
    ) -> Dict[str, Any]:
        base_prediction = self.engine.predict(
            ticker=ticker,
            model_type=model_type,
            store_result=store_result,
            horizon_days=5,
        )

        horizons = {}
        for label in ("1d", "5d", "20d"):
            horizons[label] = self._build_horizon_payload(base_prediction, self._profile(label))

        directions = {item["direction"] for item in horizons.values()}
        confidence_values = [item["confidence"] for item in horizons.values()]

        payload: Dict[str, Any] = {
            "ticker": ticker.upper(),
            "prediction_date": base_prediction.get("prediction_date"),
            "horizons": horizons,
            "consistency": len(directions) == 1,
            "overall_confidence": float(sum(confidence_values) / len(confidence_values)),
            "model_type": base_prediction.get("model_type", model_type),
        }

        if include_explanation:
            payload["explanation"] = self.engine.explain_prediction(ticker, model_type=model_type)

        return payload