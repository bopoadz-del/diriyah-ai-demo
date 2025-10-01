from __future__ import annotations

from fastapi import APIRouter


router = APIRouter()


@router.get("/speech/diagnostics")
def speech_diagnostics() -> dict[str, str]:
    """Return a stubbed response indicating the speech pipeline is mocked."""

    return {"status": "stubbed", "detail": "Speech pipeline not available in tests"}
