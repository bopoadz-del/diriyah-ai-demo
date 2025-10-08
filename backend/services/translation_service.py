"""Translation utilities supporting Arabic and English workflows."""
from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from threading import Lock
from typing import Dict, List

try:
    from deep_translator import GoogleTranslator
except ImportError:  # pragma: no cover - optional dependency in tests
    GoogleTranslator = None  # type: ignore[assignment]

try:
    from langdetect import DetectorFactory, LangDetectException, detect
except ImportError:  # pragma: no cover - optional dependency in tests
    DetectorFactory = None  # type: ignore[assignment]

    class LangDetectException(Exception):
        """Fallback exception when langdetect is unavailable."""

    def detect(_text: str) -> str:
        return "en"

try:
    from openai import OpenAI
except ImportError:  # pragma: no cover - optional dependency for offline tests
    OpenAI = None  # type: ignore[assignment]


logger = logging.getLogger(__name__)
if DetectorFactory is not None:
    DetectorFactory.seed = 42  # ensure language detection is deterministic


@dataclass(slots=True)
class _CacheEntry:
    """Simple in-memory cache entry."""

    value: str


class TranslationService:
    """Service orchestrating language detection and translation."""

    def __init__(self) -> None:
        self._client = None
        api_key = os.getenv("OPENAI_API_KEY")
        if OpenAI is not None and api_key:
            try:
                self._client = OpenAI(api_key=api_key)
            except Exception:  # pragma: no cover - defensive safeguard
                logger.exception("Failed to initialise OpenAI client for translation fallbacks.")
                self._client = None
        self._cache: Dict[str, _CacheEntry] = {}
        self._lock = Lock()

    def translate(self, text: str, target_lang: str = "ar") -> str:
        """Translate ``text`` into ``target_lang`` leveraging cached results."""

        if not text:
            return ""

        cache_key = f"{target_lang}:{text}"
        with self._lock:
            cached = self._cache.get(cache_key)
        if cached is not None:
            return cached.value

        try:
            source_lang = self._detect_language(text)
        except LangDetectException:
            source_lang = target_lang if target_lang else "en"

        if source_lang == target_lang:
            translated = text
        else:
            translated = self._google_translate(text, source_lang, target_lang)

        with self._lock:
            self._cache[cache_key] = _CacheEntry(value=translated)
        return translated

    def translate_batch(self, texts: List[str], target_lang: str = "ar") -> List[str]:
        """Translate an iterable of ``texts`` efficiently via caching."""

        return [self.translate(text, target_lang) for text in texts]

    def translate_document(self, doc_path: str, target_lang: str = "ar") -> Dict[str, str]:
        """Placeholder for structured document translation workflows."""

        raise NotImplementedError(
            "Document translation is not yet implemented. Extract text and call ``translate`` instead."
        )

    def _detect_language(self, text: str) -> str:
        return detect(text)

    def _google_translate(self, text: str, source_lang: str, target_lang: str) -> str:
        if GoogleTranslator is None:
            logger.warning("deep-translator is unavailable; skipping translation.")
            return text

        try:
            translator = GoogleTranslator(source=source_lang, target=target_lang)
            return translator.translate(text)
        except Exception:  # pragma: no cover - network/runtime failures
            logger.exception("GoogleTranslator failed; returning original text.")
            return text


__all__ = ["TranslationService"]
