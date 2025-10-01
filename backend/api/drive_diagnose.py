from fastapi import APIRouter

router = APIRouter()


@router.get("/drive/diagnostics")
def drive_diagnostics() -> dict[str, str]:
    """Return a stubbed response representing drive diagnostics."""

    return {"status": "ok", "detail": "Drive diagnostics not implemented in tests"}
