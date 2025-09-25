import random
from typing import Dict

class ProjectIntelligence:
    def analyze(self, project: str) -> Dict:
        risks = ["low", "medium", "high"]
        forecast_budget = 1_000_000 + random.randint(-100_000, 200_000)
        resource_efficiency = round(random.uniform(0.6, 0.95), 2)
        quality_risk = random.choice(risks)
        return {
            "project": project,
            "timeline_risk": random.choice(risks),
            "budget_forecast": forecast_budget,
            "resource_efficiency": resource_efficiency,
            "quality_risk": quality_risk,
            "insight": f"Project {project}: {quality_risk} quality risk, budget forecast {forecast_budget}, resources efficiency {resource_efficiency}"
        }

project_intel = ProjectIntelligence()
