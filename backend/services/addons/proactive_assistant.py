from datetime import datetime, timedelta
from typing import List, Dict, Callable

class ProactiveAssistant:
    def __init__(self):
        self.triggers: List[Dict] = []

    def add_trigger(self, condition_func: Callable[[Dict], bool], message: str):
        self.triggers.append({"condition": condition_func, "message": message})

    def check_triggers(self, context: Dict) -> List[str]:
        out = []
        for trig in self.triggers:
            try:
                if trig["condition"](context):
                    out.append(trig["message"])
            except Exception:
                pass
        return out

proactive_assistant = ProactiveAssistant()
proactive_assistant.add_trigger(lambda ctx: ctx.get("last_update") == "CAD", "The CAD design was updated — recalc materials?")
proactive_assistant.add_trigger(
    lambda ctx: ctx.get("deadline") and isinstance(ctx["deadline"], str),
    "Approval deadline approaching — send reminders?"
)
