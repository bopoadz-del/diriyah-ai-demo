from typing import Dict

class AlertResolver:
    def __init__(self):
        self.suggestions_map = {
            "boq_cad_mismatch": [
                "Run reconciliation report",
                "Contact structural engineer",
                "Check version history for changes"
            ],
            "schedule_delay": [
                "Review critical path in Primavera",
                "Reallocate resources",
                "Escalate to project manager"
            ],
            "budget_overrun": [
                "Check latest BOQ entries",
                "Compare with contract allowances",
                "Escalate to finance team"
            ]
        }

    def suggest(self, alert: Dict) -> Dict:
        t = alert.get("type")
        alert["suggestions"] = self.suggestions_map.get(t, ["No suggestions available"])
        return alert

alert_resolver = AlertResolver()
