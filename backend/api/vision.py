from __future__ import annotations

from fastapi import APIRouter

router = APIRouter()


@router.get("/vision/diagnostics")
def vision_diagnostics() -> dict[str, str]:
    """Return a stubbed response indicating the vision pipeline is mocked."""

    return {"status": "stubbed", "detail": "Vision pipeline not available in tests"}
