from __future__ import annotations

from fastapi import APIRouter

router = APIRouter()


@router.get("/drive/diagnose")
def drive_diagnose() -> dict[str, str]:
    """Return a stubbed response representing drive diagnostics."""

    return {
        "status": "error",
        "detail": "Drive diagnostics is not available in tests",
    }

