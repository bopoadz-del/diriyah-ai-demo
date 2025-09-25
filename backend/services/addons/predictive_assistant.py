from collections import defaultdict
from typing import Dict

class PredictiveAssistant:
    def __init__(self):
        self.intent_sequences = defaultdict(lambda: defaultdict(int))

    def record_intent(self, current_intent: str, next_intent: str):
        self.intent_sequences[current_intent][next_intent] += 1

    def suggest_next(self, last_intent: str, threshold: float = 0.6) -> Dict:
        if last_intent not in self.intent_sequences:
            return {}
        counts = self.intent_sequences[last_intent]
        total = sum(counts.values())
        if total == 0:
            return {}
        next_intent, count = max(counts.items(), key=lambda x: x[1])
        conf = count / total
        if conf >= threshold:
            return {"suggestion": next_intent, "confidence": conf}
        return {}

predictive_assistant = PredictiveAssistant()
