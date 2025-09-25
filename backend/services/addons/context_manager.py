from collections import deque
from typing import Dict

class ContextManager:
    def __init__(self, max_history: int = 20):
        self.history = deque(maxlen=max_history)

    def add_turn(self, user_input: str, intent: Dict):
        self.history.append({"user": user_input, "intent": intent})

    def resolve_intent(self, current_intent: Dict) -> Dict:
        # Simple disambiguation example
        if current_intent.get("intent") == "ADD_MATERIAL":
            for h in reversed(self.history):
                u = h["user"].lower()
                if "foundation" in u:
                    current_intent["resolved_service"] = "CAD"
                    break
                if "budget" in u:
                    current_intent["resolved_service"] = "BOQ"
                    break
        return current_intent

context_manager = ContextManager()
