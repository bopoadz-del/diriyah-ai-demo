"""Intent classification facade exposing a bilingual classifier."""
from __future__ import annotations

from backend.services.arabic_nlp_service import BilingualIntentClassifier, ExistingClassifier


classifier = BilingualIntentClassifier(english_classifier=ExistingClassifier())

__all__ = ["classifier"]
