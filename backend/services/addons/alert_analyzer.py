from typing import Dict, List

class AlertAnalyzer:
    def prioritize(self, alert: Dict) -> Dict:
        score = 0
        if alert.get("project_criticality") == "high":
            score += 3
        if alert.get("deadline_proximity") == "urgent":
            score += 2
        if alert.get("impact_severity") == "high":
            score += 3
        if alert.get("team_capacity") == "low":
            score += 1
        if score >= 6:
            prio = "critical"
        elif score >= 3:
            prio = "medium"
        else:
            prio = "low"
        alert["priority"] = prio
        alert["score"] = score
        return alert

    def group_related(self, alerts: List[Dict]) -> List[Dict]:
        grouped = []
        seen = set()
        for a in alerts:
            key = a.get("type")
            if key in seen:
                continue
            related = [x for x in alerts if x.get("type") == key]
            if len(related) > 1:
                grouped.append({"type": key, "alerts": related, "grouped": True})
            else:
                grouped.append(a)
            seen.add(key)
        return grouped

alert_analyzer = AlertAnalyzer()
