"""Intent classification helpers optimised for Render deployments."""

from __future__ import annotations

import importlib
import importlib.util
import logging
import re
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, Iterable, Optional, Tuple

logger = logging.getLogger(__name__)


_TFIDF_VECTORIZER_PATH = Path("models/tfidf_vectorizer.pkl")
_TFIDF_CLASSIFIER_PATH = Path("models/tfidf_classifier.pkl")
_BERT_MODEL_ID = "distilbert-base-uncased-finetuned-sst-2-english"


def _normalise_text(text: str) -> str:
    return text.lower().strip()


@lru_cache(maxsize=1)
def _joblib_module() -> Any | None:
    if importlib.util.find_spec("joblib") is None:
        logger.info("joblib is not installed; TF-IDF classifier disabled")
        return None
    try:
        return importlib.import_module("joblib")
    except Exception as exc:  # pragma: no cover - optional dependency issues
        logger.warning("Unable to import joblib: %s", exc)
        return None


def _load_joblib_artifact(path: Path, *, label: str) -> Any | None:
    joblib_module = _joblib_module()
    if joblib_module is None:
        return None
    try:
        return joblib_module.load(path)
    except FileNotFoundError:
        logger.info("%s artifact missing at %s", label, path)
    except Exception as exc:  # pragma: no cover - defensive logging
        logger.warning("Failed to load %s artifact: %s", label, exc)
    return None


@lru_cache(maxsize=1)
def _tfidf_resources() -> Tuple[Any | None, Any | None]:
    vectorizer = _load_joblib_artifact(_TFIDF_VECTORIZER_PATH, label="TF-IDF vectorizer")
    classifier = _load_joblib_artifact(_TFIDF_CLASSIFIER_PATH, label="TF-IDF classifier")
    if vectorizer is None or classifier is None:
        return None, None
    return vectorizer, classifier


def _transformers_available() -> bool:
    return importlib.util.find_spec("transformers") is not None


@lru_cache(maxsize=1)
def _bert_pipeline() -> Any | None:
    if not _transformers_available():
        logger.info("Transformers library not available; BERT intent classifier disabled")
        return None
    transformers = importlib.import_module("transformers")
    pipeline = getattr(transformers, "pipeline", None)
    if pipeline is None:
        logger.warning("transformers.pipeline function is unavailable")
        return None
    try:
        return pipeline("text-classification", model=_BERT_MODEL_ID)
    except Exception as exc:  # pragma: no cover - network/model download issues
        logger.warning("Unable to initialise BERT intent classifier: %s", exc)
        return None


RULE_KEYWORDS: Dict[str, str] = {
    "approve": "APPROVAL",
    "rollback": "ROLLBACK",
    "recalculate": "RECALCULATE",
    "validation": "VALIDATION",
    "update cad": "CAD_UPDATE",
    "update boq": "BOQ_UPDATE",
}


def _iter_rule_matches(text: str) -> Iterable[Tuple[str, str]]:
    normalised = _normalise_text(text)
    for keyword, intent in RULE_KEYWORDS.items():
        if re.search(rf"\b{re.escape(keyword)}\b", normalised):
            yield keyword, intent


def rule_based_intent(text: str) -> Optional[str]:
    for _keyword, intent in _iter_rule_matches(text):
        return intent
    return None


def classify_intent(text: str) -> Dict[str, Any]:
    results: list[Dict[str, Any]] = []

    rule_intent = rule_based_intent(text)
    if rule_intent:
        return {"intent": rule_intent, "confidence": 1.0, "source": "rule"}

    vectorizer, classifier = _tfidf_resources()
    if vectorizer is not None and classifier is not None:
        try:
            matrix = vectorizer.transform([text])
            prediction = classifier.predict(matrix)[0]
            probabilities = classifier.predict_proba(matrix)[0]
            confidence = float(max(probabilities))
        except Exception as exc:  # pragma: no cover - corrupt artifacts
            logger.warning("TF-IDF intent classification failed: %s", exc)
        else:
            results.append({"intent": prediction, "confidence": confidence, "source": "tfidf"})

    bert_classifier = _bert_pipeline()
    if bert_classifier is not None:
        try:
            bert_result = bert_classifier(text, truncation=True)[0]
            results.append(
                {
                    "intent": bert_result["label"],
                    "confidence": float(bert_result["score"]),
                    "source": "bert",
                }
            )
        except Exception as exc:  # pragma: no cover - runtime issues
            logger.warning("BERT intent classification failed: %s", exc)

    if results:
        return max(results, key=lambda item: item["confidence"])

    return {"intent": "GENERAL", "confidence": 0.5, "source": "fallback"}


def classify_intent_with_explanation(text: str) -> Dict[str, Any]:
    result = classify_intent(text)
    source = result.get("source")
    if source == "rule":
        result["explanation"] = "Matched rule for keyword in text."
    elif source == "tfidf":
        result["explanation"] = (
            f"TF-IDF classifier chose {result['intent']} at confidence {result['confidence']:.2f}."
        )
    elif source == "bert":
        result["explanation"] = (
            f"BERT classified with label {result['intent']} and score {result['confidence']:.2f}."
        )
    else:
        result["explanation"] = "Heuristic fallback."
    return result
