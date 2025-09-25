import re
from typing import Dict, Callable, Any
from .intent_classifier import classifier

class IntentRouter:
    def __init__(self):
        self.registry: Dict[str, Dict] = {}

    def register(self, name: str, patterns: list[str], handler: Callable):
        self.registry[name] = {"patterns": patterns, "handler": handler}

    def route(self, message: str, context: dict = None) -> Any:
        # Regex-based routing
        for name, entry in self.registry.items():
            for pattern in entry["patterns"]:
                if re.search(pattern, message, re.IGNORECASE):
                    return entry["handler"](message, context or {})

        # Fallback: classifier prediction
        label, conf = classifier.predict(message)
        if label and conf > 0.7 and label in self.registry:
            return self.registry[label]["handler"](message, context or {})

        return {"clarify": f"No clear intent. Closest: {label} ({conf:.2f})" if label else "No model available"}

# Global router instance
router = IntentRouter()
