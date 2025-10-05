from __future__ import annotations

from fastapi import APIRouter

router = APIRouter()


 codex/add-/projects/scan-drive-endpoint
_STUBBED_DIAGNOSE_RESPONSE: dict[str, str] = {
    "status": "error",
    "detail": "Drive diagnostics are not available in the stubbed environment.",
}


@router.get("/drive/diagnose")
def drive_diagnose() -> dict[str, str]:
    """Return a stubbed response representing drive diagnostics."""

    return _STUBBED_DIAGNOSE_RESPONSE


@router.get("/drive/diagnostics")
def drive_diagnostics() -> dict[str, str]:
    """Backward-compatible alias for legacy clients."""

    return _STUBBED_DIAGNOSE_RESPONSE

@router.get("/drive/diagnose")
def drive_diagnose() -> dict[str, str]:
    """Return a stubbed response representing drive diagnostics."""

    return {
        "status": "error",
        "detail": "Drive diagnostics is not available in tests",
    }
      main

