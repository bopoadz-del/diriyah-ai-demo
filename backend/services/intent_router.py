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
        elif _is_runtime_query(lower_text):
            intent = "RUNTIME_EXECUTE"

        return {"intent": intent, "message": message, "project_id": project_id}


# Runtime query patterns for code generation
_RUNTIME_PATTERNS = [
    r"calculate.*variance",
    r"what.*if.*(increase|decrease)",
    r"forecast.*(delay|slip|cost)",
    r"monte carlo|simulation",
    r"analyze.*p&l",
    r"run.*analysis",
    r"compute.*total",
    r"sum.*of",
    r"average.*of",
    r"sensitivity.*analysis",
    r"what\'?s the (cost|schedule|budget)",
]


def _is_runtime_query(text: str) -> bool:
    """Check if text matches runtime query patterns."""
    for pattern in _RUNTIME_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE):
            return True
    return False


router = IntentRouter()

__all__ = ["IntentRouter", "router"]
