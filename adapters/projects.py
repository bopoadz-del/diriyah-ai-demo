# adapters/projects.py
"""
Minimal demo adapter for projects.
This keeps Render happy and lets the UI show some sample projects.
Replace these with real Drive/OneDrive lookups later.
"""

from typing import List, Dict

def fetch_projects() -> List[Dict]:
    # Demo/sample data to keep the app running
    return [
        {
            "id": 1,
            "name": "Riverfront Office Complex",
            "location": "Riyadh",
            "description": "12-story commercial building",
            "status": "On Track",
            "progress": 75,
            "deadline": "2025-12-15",
            "cloudService": "google",
            "riskLevel": "low",
        },
        {
            "id": 2,
            "name": "Hilltop Residential Tower",
            "location": "Diriyah",
            "description": "Luxury residential tower",
            "status": "On Track",
            "progress": 45,
            "deadline": "2026-02-28",
            "cloudService": "onedrive",
            "riskLevel": "medium",
        },
        {
            "id": 3,
            "name": "Community Hospital Renovation",
            "location": "Jeddah",
            "description": "Hospital expansion and renovation",
            "status": "Delayed",
            "progress": 30,
            "deadline": "2026-01-15",
            "cloudService": "google",
            "riskLevel": "high",
        },
        {
            "id": 4,
            "name": "Tech Campus Expansion",
            "location": "Khobar",
            "description": "New tech campus buildings",
            "status": "On Track",
            "progress": 72,
            "deadline": "2026-03-10",
            "cloudService": "onedrive",
            "riskLevel": "low",
        },
    ]
