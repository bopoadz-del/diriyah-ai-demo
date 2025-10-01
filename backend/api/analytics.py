"""Analytics endpoints that back the debugging dashboard."""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Dict, List

from fastapi import APIRouter

router = APIRouter()

_TIMELINE_TEMPLATE: List[Dict[str, int]] = [
    {"label": "Mon", "value": 6},
    {"label": "Tue", "value": 9},
    {"label": "Wed", "value": 7},
    {"label": "Thu", "value": 12},
    {"label": "Fri", "value": 8},
]


@router.get("/analytics/summary")
def analytics_summary() -> Dict[str, object]:
    """Return a curated analytics payload for the Render demo UI."""

    now = datetime.utcnow()
    timeline = [
        {
            "label": day["label"],
            "value": day["value"],
            "timestamp": (now - timedelta(days=len(_TIMELINE_TEMPLATE) - index)).isoformat() + "Z",
        }
        for index, day in enumerate(_TIMELINE_TEMPLATE, start=1)
    ]

    metrics = {
        "documents_indexed": 186,
        "alerts_open": 2,
        "meetings_transcribed": 8,
        "response_time_ms": 780,
        "satisfaction": 94,
        "drive_sync": (now - timedelta(hours=3)).isoformat() + "Z",
    }

    return {"status": "ok", "metrics": metrics, "timeline": timeline}
