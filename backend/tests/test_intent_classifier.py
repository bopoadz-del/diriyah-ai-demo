from pathlib import Path

import pytest

from backend.services.intent_classifier import classifier


MODEL_DIR = Path("backend/models")
MODEL_PATH = MODEL_DIR / "intent_model.pkl"
VECTORIZER_PATH = MODEL_DIR / "vectorizer.pkl"


pytestmark = pytest.mark.skipif(
    not (MODEL_PATH.exists() and VECTORIZER_PATH.exists()),
    reason="Intent classifier artifacts are not available in the stub environment.",
)


def test_model_files_exist() -> None:
    assert MODEL_PATH.exists()
    assert VECTORIZER_PATH.exists()


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("run cad takeoff", "cad_takeoff"),
        ("upload boq", "boq_parser"),
        ("import xer", "primavera"),
        ("analyze ifc model", "bim"),
        ("search aconex", "aconex"),
        ("analyze photo", "vision"),
        ("merge cad and boq", "consolidated_takeoff"),
        ("project kpi dashboard", "analytics_engine"),
        ("raise compliance alert", "alerts_engine"),
        ("semantic search project data", "rag_engine"),
    ],
)
def test_intent_predictions(text: str, expected: str) -> None:
    label, confidence = classifier.predict(text)
    assert label == expected
    assert confidence > 0.6
