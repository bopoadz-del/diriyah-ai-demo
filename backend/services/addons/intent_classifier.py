import re
import joblib
import numpy as np
from typing import Dict

# Optional heavy deps
try:
    from transformers import pipeline
except Exception:  # pragma: no cover
    pipeline = None

# Load TF-IDF artifacts if present
try:
    tfidf_vectorizer = joblib.load("models/tfidf_vectorizer.pkl")
    tfidf_classifier = joblib.load("models/tfidf_classifier.pkl")
except Exception:
    tfidf_vectorizer, tfidf_classifier = None, None

# BERT pipeline (falls back if unavailable)
if pipeline:
    try:
        bert_classifier = pipeline("text-classification", model="distilbert-base-uncased-finetuned-sst-2-english")
    except Exception:
        bert_classifier = None
else:
    bert_classifier = None

# Rule-based intents
RULES = {
    "approve": "APPROVAL",
    "rollback": "ROLLBACK",
    "recalculate": "RECALCULATE",
    "validation": "VALIDATION",
    "update cad": "CAD_UPDATE",
    "update boq": "BOQ_UPDATE",
}

def rule_based_intent(text: str) -> str | None:
    t = text.lower()
    for keyword, intent in RULES.items():
        if re.search(rf"\b{re.escape(keyword)}\b", t):
            return intent
    return None

def classify_intent(text: str) -> Dict:
    results = []

    # 1. Rule-based (highest priority)
    rule_intent = rule_based_intent(text)
    if rule_intent:
        return {"intent": rule_intent, "confidence": 1.0, "source": "rule"}

    # 2. TF-IDF
    if tfidf_vectorizer is not None and tfidf_classifier is not None:
        X = tfidf_vectorizer.transform([text])
        pred = tfidf_classifier.predict(X)[0]
        conf = float(np.max(tfidf_classifier.predict_proba(X)))
        results.append({"intent": pred, "confidence": conf, "source": "tfidf"})

    # 3. BERT (if available)
    if bert_classifier is not None:
        try:
            bert_result = bert_classifier(text, truncation=True)[0]
            results.append({
                "intent": bert_result["label"],
                "confidence": float(bert_result["score"]),
                "source": "bert"
            })
        except Exception:
            pass

    if results:
        best = max(results, key=lambda x: x["confidence"])
        return best
    # Fallback
    return {"intent": "GENERAL", "confidence": 0.5, "source": "fallback"}

def classify_intent_with_explanation(text: str) -> Dict:
    res = classify_intent(text)
    # Explanations
    if res["source"] == "rule":
        res["explanation"] = f"Matched rule for keyword in text."
    elif res["source"] == "tfidf":
        res["explanation"] = f"TF-IDF classifier chose {res['intent']} at confidence {res['confidence']:.2f}."
    elif res["source"] == "bert":
        res["explanation"] = f"BERT classified with label {res['intent']} and score {res['confidence']:.2f}."
    else:
        res["explanation"] = "Heuristic fallback."
    return res
