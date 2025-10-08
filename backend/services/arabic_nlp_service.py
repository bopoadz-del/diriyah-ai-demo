"""Arabic natural language processing utilities."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

try:
    from langdetect import LangDetectException, detect
except ImportError:  # pragma: no cover - optional dependency in tests
    class LangDetectException(Exception):
        """Fallback exception raised when language detection is unavailable."""

    def detect(_text: str) -> str:
        return "en"

logger = logging.getLogger(__name__)


def _safe_import(module: str, symbol: str | None = None) -> Any:
    try:
        mod = __import__(module, fromlist=[symbol] if symbol else [])
        if symbol:
            return getattr(mod, symbol)
        return mod
    except Exception:  # pragma: no cover - optional dependency
        return None


torch = _safe_import("torch")
transformers = _safe_import("transformers")
camel_sentiment = _safe_import("camel_tools.sentiment", "SentimentAnalyzer")
camel_ner = _safe_import("camel_tools.ner", "NERecognizer")
camel_tokenizer = _safe_import("camel_tools.tokenizers.word", "simple_word_tokenize")


@dataclass
class IntentPrediction:
    intent: str
    confidence: float
    tokens: List[str]


class ArabicNLPUnavailable(RuntimeError):
    """Raised when advanced Arabic NLP tooling cannot be initialised."""


class ArabicNLPService:
    """Encapsulates Arabic-specific NLP capabilities with safe fallbacks."""

    def __init__(self) -> None:
        self._tokenizer = camel_tokenizer
        self._sentiment_analyzer = None
        self._ner = None
        self._token_classification_pipeline = None
        self._initialise_models()
        self._keyword_intents: Dict[str, IntentPrediction] = {
            "تصميم": IntentPrediction("design_review", 0.74, ["تصميم"]),
            "جدول": IntentPrediction("schedule_analysis", 0.7, ["جدول"]),
            "تكلفة": IntentPrediction("cost_analysis", 0.72, ["تكلفة"]),
            "تقدم": IntentPrediction("progress_update", 0.76, ["تقدم"]),
        }

    def _initialise_models(self) -> None:
        if transformers is None or torch is None:
            logger.info("Transformers or torch is unavailable; using heuristic Arabic NLP fallbacks.")
            return

        try:
            AutoTokenizer = getattr(transformers, "AutoTokenizer")
            AutoModelForSequenceClassification = getattr(
                transformers, "AutoModelForSequenceClassification"
            )
            self._tokenizer = AutoTokenizer.from_pretrained("aubmindlab/bert-base-arabertv2")
            self._token_classification_pipeline = AutoModelForSequenceClassification.from_pretrained(
                "aubmindlab/bert-base-arabertv2"
            )
        except Exception:  # pragma: no cover - model downloads disabled in CI
            logger.warning("Unable to load Arabic BERT model; falling back to heuristics.", exc_info=True)
            self._tokenizer = camel_tokenizer
            self._token_classification_pipeline = None

        if camel_sentiment is not None:
            try:
                self._sentiment_analyzer = camel_sentiment.pretrained()
            except Exception:  # pragma: no cover
                logger.warning("Failed to load CAMeL sentiment analyzer; using neutral fallback.")
                self._sentiment_analyzer = None

        if camel_ner is not None:
            try:
                self._ner = camel_ner.pretrained()
            except Exception:  # pragma: no cover
                logger.warning("Failed to load CAMeL NER; named entity extraction disabled.")
                self._ner = None

    def analyze_intent(self, text: str) -> Dict[str, Any]:
        if not text:
            return {"intent": "unknown", "confidence": 0.0, "tokens": []}

        heuristic = self._keyword_intent(text)
        if heuristic is not None:
            return {
                "intent": heuristic.intent,
                "confidence": heuristic.confidence,
                "tokens": heuristic.tokens,
            }

        if self._tokenizer is None or self._token_classification_pipeline is None or torch is None:
            return {"intent": "general_arabic", "confidence": 0.55, "tokens": self._tokenise(text)}

        try:
            tokenizer = self._tokenizer
            model = self._token_classification_pipeline
            inputs = tokenizer(text, return_tensors="pt", truncation=True, max_length=512)
            with torch.no_grad():
                outputs = model(**inputs)
                scores = torch.nn.functional.softmax(outputs.logits, dim=-1)
            intent_index = int(torch.argmax(scores).item())
            confidence = float(scores[0][intent_index].item())
            intent = self._map_intent(intent_index)
            return {"intent": intent, "confidence": confidence, "tokens": self._tokenise(text)}
        except Exception:  # pragma: no cover - inference failure fallback
            logger.exception("Arabic transformer inference failed; defaulting to heuristic intent.")
            return {"intent": "general_arabic", "confidence": 0.5, "tokens": self._tokenise(text)}

    def extract_entities(self, text: str) -> List[Dict[str, Any]]:
        if not text:
            return []

        if self._ner is None:
            return []

        try:
            entities = self._ner.predict([text])[0]
        except Exception:  # pragma: no cover
            logger.exception("Arabic NER prediction failed; returning empty entity list.")
            return []

        return [
            {
                "text": ent.text,
                "type": ent.type,
                "start": ent.start,
                "end": ent.end,
            }
            for ent in entities
        ]

    def sentiment_analysis(self, text: str) -> Dict[str, Any]:
        if not text:
            return {"sentiment": "neutral", "score": 0.0}

        if self._sentiment_analyzer is None:
            return {"sentiment": "neutral", "score": 0.5}

        try:
            sentiment = self._sentiment_analyzer.predict([text])[0]
            return {"sentiment": sentiment.label, "score": sentiment.score}
        except Exception:  # pragma: no cover
            logger.exception("Arabic sentiment analysis failed; defaulting to neutral.")
            return {"sentiment": "neutral", "score": 0.5}

    def _tokenise(self, text: str) -> List[str]:
        if self._tokenizer is None:
            return text.split()
        if callable(self._tokenizer):
            try:
                return list(self._tokenizer(text))
            except Exception:  # pragma: no cover
                logger.exception("Arabic tokeniser failed; falling back to whitespace split.")
        return text.split()

    def _keyword_intent(self, text: str) -> Optional[IntentPrediction]:
        for keyword, prediction in self._keyword_intents.items():
            if keyword in text:
                return prediction
        return None

    def _map_intent(self, index: int) -> str:
        mapping = {
            0: "general_arabic",
            1: "progress_update",
            2: "issue_tracking",
            3: "risk_management",
        }
        return mapping.get(index, "general_arabic")


class ExistingClassifier:
    """Placeholder English classifier that mirrors the historic behaviour."""

    def predict(self, text: str) -> tuple[str, float]:
        # In production this would load persisted scikit-learn artifacts.
        return ("unknown", 0.0)


class BilingualIntentClassifier:
    """Routes intent analysis between Arabic and English pipelines."""

    def __init__(self, english_classifier: Optional[Any] = None) -> None:
        self.arabic_nlp = ArabicNLPService()
        self.english_classifier = english_classifier or ExistingClassifier()

    def classify(self, text: str) -> Dict[str, Any]:
        language = self._detect_language(text)
        if language == "ar":
            analysis = self.arabic_nlp.analyze_intent(text)
            return {
                "intent": analysis["intent"],
                "confidence": analysis["confidence"],
                "language": "ar",
                "tokens": analysis.get("tokens", []),
            }

        label, confidence = self.english_classifier.predict(text)
        return {"intent": label, "confidence": float(confidence), "language": language or "en"}

    def predict(self, text: str) -> tuple[str, float]:
        result = self.classify(text)
        return result["intent"], float(result["confidence"])

    def _detect_language(self, text: str) -> str:
        if not text:
            return "en"
        try:
            return detect(text)
        except LangDetectException:
            return "en"


__all__ = [
    "ArabicNLPService",
    "ArabicNLPUnavailable",
    "BilingualIntentClassifier",
    "ExistingClassifier",
]
