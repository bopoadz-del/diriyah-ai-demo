from __future__ import annotations

from typing import Any, Mapping

from fastapi import APIRouter
from pydantic import BaseModel, Field

from backend.services.advanced_intelligence import suite


class AdvancedIntelligenceRequest(BaseModel):
    query: str = Field(..., description="Primary user question or objective")
    goal: str | None = Field(
        default=None,
        description="Optional explicit goal to anchor planning",
    )
    context: Mapping[str, Any] | None = Field(
        default=None,
        description="Supplemental context used by the simulated engines",
    )


router = APIRouter()


@router.post("/advanced-intelligence/analyze")
async def analyze_features(payload: AdvancedIntelligenceRequest) -> dict[str, Any]:
    """Return a consolidated set of advanced intelligence feature outputs."""

    report = suite.generate_report(payload.query, goal=payload.goal, context=payload.context)
    return {
        "query": payload.query,
        "goal": payload.goal,
        "results": report,
    }


__all__ = ["router"]
