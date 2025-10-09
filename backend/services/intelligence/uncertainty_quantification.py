"""Utilities for estimating prediction uncertainty."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, List, Optional, Sequence, Tuple
import logging
import math
import os

import numpy as np

try:  # pragma: no cover - optional dependency
    from mapie.classification import MapieClassifier
    from mapie.regression import MapieRegressor

    MAPIE_AVAILABLE = True
except Exception:  # pragma: no cover - handled gracefully
    MAPIE_AVAILABLE = False

try:  # pragma: no cover - optional dependency
    import torch
    from torch import nn
    from torch.nn import functional as F

    TORCH_AVAILABLE = True
except Exception:  # pragma: no cover - handled gracefully
    TORCH_AVAILABLE = False
    torch = None  # type: ignore
    nn = object  # type: ignore
    F = object  # type: ignore

logger = logging.getLogger(__name__)


@dataclass
class UncertaintyResult:
    """Container describing the confidence associated with a prediction."""

    prediction: Any
    confidence: float
    uncertainty: float
    confidence_interval: Tuple[float, float]
    prediction_sets: Optional[List[Any]] = None
    epistemic_uncertainty: Optional[float] = None
    aleatoric_uncertainty: Optional[float] = None
    explanation: Optional[str] = None
    should_escalate: bool = False


class UncertaintyQuantifier:
    """High level orchestrator that adds uncertainty information to predictions."""

    def __init__(self, model_type: str = "classification", confidence_level: float = 0.9) -> None:
        self.model_type = model_type
        self.confidence_level = confidence_level
        self.calibrated_model: Any | None = None
        self.conformal_predictor: Any | None = None
        self.uncertainty_threshold = float(os.getenv("UNCERTAINTY_THRESHOLD", "0.3"))

    def calibrate_model(self, base_model: Any, X_cal: np.ndarray, y_cal: Sequence[Any]) -> None:
        """Calibrate a model so downstream predictions expose reliable probabilities."""

        if self.model_type == "classification":
            from sklearn.calibration import CalibratedClassifierCV

            self.calibrated_model = CalibratedClassifierCV(base_estimator=base_model, method="isotonic", cv="prefit")
            self.calibrated_model.fit(X_cal, y_cal)

            if MAPIE_AVAILABLE:
                self.conformal_predictor = MapieClassifier(estimator=self.calibrated_model, method="lac", cv="prefit")
                self.conformal_predictor.fit(X_cal, y_cal)
        elif self.model_type == "regression":
            self.calibrated_model = base_model
            if MAPIE_AVAILABLE:
                self.conformal_predictor = MapieRegressor(estimator=base_model, method="plus", cv=5)
                self.conformal_predictor.fit(X_cal, y_cal)
        else:
            self.calibrated_model = base_model

        logger.info("Model calibrated with dataset of size %s", len(X_cal))

    def predict_with_uncertainty(self, X: np.ndarray, return_all_metrics: bool = False) -> List[UncertaintyResult]:
        """Return predictions enriched with several uncertainty metrics."""

        X = np.asarray(X)
        if X.ndim == 1:
            X = X.reshape(1, -1)

        if self.model_type == "classification":
            return self._classify_with_uncertainty(X, return_all_metrics)
        if self.model_type == "regression":
            return self._regress_with_uncertainty(X)
        if self.model_type == "deep_learning":
            return self._deep_learning_uncertainty(X)

        raise ValueError(f"Unsupported model_type: {self.model_type}")

    def _classify_with_uncertainty(self, X: np.ndarray, return_all_metrics: bool) -> List[UncertaintyResult]:
        if self.calibrated_model is not None and hasattr(self.calibrated_model, "predict_proba"):
            probas = self.calibrated_model.predict_proba(X)
        else:
            logger.debug("No calibrated model available; falling back to heuristic probabilities")
            probas = self._heuristic_probabilities(X)

        probas = np.clip(probas, 1e-9, 1)
        probas = probas / probas.sum(axis=1, keepdims=True)
        predictions = probas.argmax(axis=1)
        max_probas = probas.max(axis=1)

        entropy = -np.sum(probas * np.log(probas), axis=1)
        max_entropy = math.log(probas.shape[1]) if probas.shape[1] > 1 else 1.0
        normalized_entropy = entropy / max_entropy

        prediction_sets: List[List[Any]] | None = None
        if MAPIE_AVAILABLE and self.conformal_predictor is not None:
            _, raw_sets = self.conformal_predictor.predict(X, alpha=1 - self.confidence_level)
            prediction_sets = [list(filter(lambda value: value is not None, row)) for row in raw_sets]

        results: List[UncertaintyResult] = []
        for idx in range(X.shape[0]):
            confidence = float(max_probas[idx])
            uncertainty = float(normalized_entropy[idx])
            ci_lower = max(confidence - 0.1, 0.0)
            ci_upper = min(confidence + 0.1, 1.0)

            explanation = self._generate_explanation(confidence, uncertainty, prediction_sets[idx] if prediction_sets else None)
            should_escalate = uncertainty > self.uncertainty_threshold or confidence < 0.7

            results.append(
                UncertaintyResult(
                    prediction=int(predictions[idx]),
                    confidence=confidence,
                    uncertainty=uncertainty,
                    confidence_interval=(ci_lower, ci_upper),
                    prediction_sets=prediction_sets[idx] if prediction_sets else None,
                    epistemic_uncertainty=None,
                    aleatoric_uncertainty=uncertainty,
                    explanation=explanation,
                    should_escalate=should_escalate,
                )
            )

        return results

    def _regress_with_uncertainty(self, X: np.ndarray) -> List[UncertaintyResult]:
        if MAPIE_AVAILABLE and self.conformal_predictor is not None:
            y_pred, intervals = self.conformal_predictor.predict(X, alpha=1 - self.confidence_level)
            results: List[UncertaintyResult] = []
            for idx, prediction in enumerate(y_pred):
                lower = float(intervals[idx, 0, 0])
                upper = float(intervals[idx, 1, 0])
                interval_width = upper - lower
                scale = abs(prediction) + 1e-8
                relative_uncertainty = interval_width / scale
                confidence = max(0.0, 1.0 - relative_uncertainty)
                explanation = f"{int(self.confidence_level * 100)}% chance the value lies between {lower:.2f} and {upper:.2f}"
                results.append(
                    UncertaintyResult(
                        prediction=float(prediction),
                        confidence=confidence,
                        uncertainty=min(relative_uncertainty, 1.0),
                        confidence_interval=(lower, upper),
                        explanation=explanation,
                        should_escalate=relative_uncertainty > 0.5,
                    )
                )
            return results

        if self.calibrated_model is None or not hasattr(self.calibrated_model, "predict"):
            logger.warning("Regression uncertainty requested but no model is configured")
            return [
                UncertaintyResult(
                    prediction=0.0,
                    confidence=0.5,
                    uncertainty=0.5,
                    confidence_interval=(-1.0, 1.0),
                    explanation="No calibrated regression model available",
                    should_escalate=True,
                )
            ]

        predictions = self.calibrated_model.predict(X)
        results = []
        for value in predictions:
            lower = float(value) * 0.9
            upper = float(value) * 1.1
            explanation = "Uncertainty estimated heuristically (±10%)"
            results.append(
                UncertaintyResult(
                    prediction=float(value),
                    confidence=0.6,
                    uncertainty=0.4,
                    confidence_interval=(lower, upper),
                    explanation=explanation,
                    should_escalate=False,
                )
            )
        return results

    def _deep_learning_uncertainty(self, X: np.ndarray) -> List[UncertaintyResult]:
        if not TORCH_AVAILABLE:
            logger.warning("PyTorch is not available; returning heuristic uncertainty")
            return [
                UncertaintyResult(
                    prediction=0,
                    confidence=0.5,
                    uncertainty=0.5,
                    confidence_interval=(0.3, 0.7),
                    explanation="Deep learning uncertainty unavailable (PyTorch missing)",
                    should_escalate=True,
                )
            ]

        raise NotImplementedError("Deep learning uncertainty requires a configured Bayesian model")

    def _heuristic_probabilities(self, X: np.ndarray) -> np.ndarray:
        if X.size == 0:
            return np.array([[0.5, 0.5]])
        feature_sums = np.sum(X, axis=1)
        logits = np.vstack([feature_sums, -feature_sums]).T
        exp_logits = np.exp(logits - logits.max(axis=1, keepdims=True))
        return exp_logits / exp_logits.sum(axis=1, keepdims=True)

    def _generate_explanation(self, confidence: float, uncertainty: float, prediction_set: Optional[Sequence[Any]] = None) -> str:
        if confidence > 0.9:
            explanation = "High confidence prediction"
        elif confidence > 0.7:
            explanation = "Moderate confidence prediction"
        elif confidence > 0.5:
            explanation = "Low confidence prediction"
        else:
            explanation = "Prediction is highly uncertain"

        if prediction_set and len(prediction_set) > 1:
            formatted = ", ".join(str(item) for item in prediction_set[:3])
            if len(prediction_set) > 3:
                formatted += ", …"
            explanation += f". Alternative classes: {formatted}"
        return explanation


class BayesianUncertaintyNet(nn.Module if TORCH_AVAILABLE else object):
    """Simple Bayesian neural network using Monte Carlo dropout."""

    def __init__(self, input_dim: int, hidden_dim: int, output_dim: int, dropout_rate: float = 0.2) -> None:
        if not TORCH_AVAILABLE:  # pragma: no cover - guard for optional dependency
            raise RuntimeError("PyTorch is required to instantiate BayesianUncertaintyNet")

        super().__init__()
        self.fc1 = nn.Linear(input_dim, hidden_dim)
        self.fc2 = nn.Linear(hidden_dim, hidden_dim)
        self.fc3 = nn.Linear(hidden_dim, output_dim)
        self.dropout = nn.Dropout(dropout_rate)

    def forward(self, x: "torch.Tensor", training: bool = True) -> "torch.Tensor":
        if not TORCH_AVAILABLE:  # pragma: no cover
            raise RuntimeError("PyTorch is required to run BayesianUncertaintyNet")
        x = F.relu(self.fc1(x))
        if training:
            x = self.dropout(x)
        x = F.relu(self.fc2(x))
        if training:
            x = self.dropout(x)
        return self.fc3(x)

    def predict_with_uncertainty(self, x: "torch.Tensor", n_samples: int = 100) -> Tuple["torch.Tensor", "torch.Tensor"]:
        if not TORCH_AVAILABLE:  # pragma: no cover
            raise RuntimeError("PyTorch is required to run BayesianUncertaintyNet")

        self.train()
        predictions = []
        with torch.no_grad():
            for _ in range(n_samples):
                predictions.append(self.forward(x))
        stacked = torch.stack(predictions)
        return stacked.mean(dim=0), stacked.std(dim=0)
