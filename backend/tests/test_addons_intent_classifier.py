"""Tests for the lightweight Render-friendly intent classifier."""

from __future__ import annotations

from backend.services.addons import intent_classifier


def reset_caches() -> None:
    intent_classifier._joblib_module.cache_clear()  # type: ignore[attr-defined]
    intent_classifier._tfidf_resources.cache_clear()  # type: ignore[attr-defined]
    intent_classifier._bert_pipeline.cache_clear()  # type: ignore[attr-defined]


def test_rule_based_intent_detected() -> None:
    reset_caches()
    result = intent_classifier.classify_intent("Please approve the drawing")
    assert result["intent"] == "APPROVAL"
    assert result["source"] == "rule"
    assert result["confidence"] == 1.0


def test_fallback_when_models_unavailable() -> None:
    reset_caches()
    result = intent_classifier.classify_intent("Unknown request that lacks training data")
    assert result["intent"] == "GENERAL"
    assert result["source"] == "fallback"
    assert result["confidence"] == 0.5
