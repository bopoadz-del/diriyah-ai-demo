from __future__ import annotations

from fastapi import APIRouter

router = APIRouter()


@router.get("/drive/scan/status")
def drive_scan_status() -> dict[str, str]:
    """Return a stubbed response representing drive scanning state."""

    return {"status": "idle", "detail": "Drive scanning is not available in tests"}

