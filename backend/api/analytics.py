"""Analytics endpoints exposing the in-memory activity log."""

from __future__ import annotations

from collections import Counter
from typing import Any, Dict

from fastapi import APIRouter

from backend.services import stub_state

router = APIRouter()


@router.get("/analytics")
def list_analytics() -> list[Dict[str, Any]]:
    return sorted(stub_state.list_analytics(), key=lambda entry: entry["id"])


@router.get("/analytics/summary")
def analytics_summary() -> Dict[str, Any]:
    logs = stub_state.list_analytics()
    counts = dict(Counter(log["action"] for log in logs))
    return {
        "status": "ok",
        "counts": counts,
        "total": len(logs),
    }
