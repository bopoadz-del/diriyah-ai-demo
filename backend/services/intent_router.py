from __future__ import annotations

import re
from collections.abc import Callable, Iterable


class IntentRouter:
    def __init__(self) -> None:
        self._services: list[tuple[str, list[re.Pattern[str]], Callable[..., object]]] = []

    def register(
        self, name: str, patterns: Iterable[str] | str, handler: Callable[..., object]
    ) -> None:
        normalized_patterns = [patterns] if isinstance(patterns, str) else list(patterns)
        compiled_patterns = [re.compile(pattern, re.IGNORECASE) for pattern in normalized_patterns]
        self._services.append((name, compiled_patterns, handler))

    def route(self, message: str, project_id: str | None = None):
        text = message if isinstance(message, str) else "" if message is None else str(message)

        for name, patterns, _ in self._services:
            if any(pattern.search(text) for pattern in patterns):
                return {"intent": name, "message": message, "project_id": project_id}

        intent = "unknown"
        lower_text = text.lower()
        if "upload" in lower_text:
            intent = "UPLOAD_DOC"
        elif "image" in lower_text or "photo" in lower_text:
            intent = "VISION_ANALYZE"
        elif "audio" in lower_text or "mic" in lower_text:
            intent = "TRANSCRIBE_AUDIO"

        return {"intent": intent, "message": message, "project_id": project_id}


router = IntentRouter()

__all__ = ["IntentRouter", "router"]
