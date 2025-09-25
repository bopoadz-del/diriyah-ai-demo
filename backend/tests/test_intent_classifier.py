import os
import pytest
from backend.services.intent_classifier import classifier

def test_model_files_exist():
    model_dir = os.path.join("backend", "models")
    assert os.path.exists(os.path.join(model_dir, "intent_model.pkl"))
    assert os.path.exists(os.path.join(model_dir, "vectorizer.pkl"))

@pytest.mark.parametrize("text,expected", [
    ("run cad takeoff","cad_takeoff"),
    ("upload boq","boq_parser"),
    ("import xer","primavera"),
    ("analyze ifc model","bim"),
    ("search aconex","aconex"),
    ("analyze photo","vision"),
    ("merge cad and boq","consolidated_takeoff"),
    ("project kpi dashboard","analytics_engine"),
    ("raise compliance alert","alerts_engine"),
    ("semantic search project data","rag_engine"),
])
def test_intent_predictions(text, expected):
    label, conf = classifier.predict(text)
    assert label == expected
    assert conf > 0.6
