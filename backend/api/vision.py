from __future__ import annotations

from fastapi import APIRouter

from backend.connectors.factory import get_connector
from backend.services.vision import VisionClient, VisionConfigurationError, VisionError

router = APIRouter()


def _is_stubbed(connector: object) -> bool:
    return isinstance(connector, dict) and connector.get("status") == "stubbed"


@router.get("/vision/diagnostics")
def vision_diagnostics() -> dict[str, str]:
    """Return a response indicating the status of the vision connector."""

    try:
        connector = get_connector("vision")
    except (ValueError, VisionConfigurationError) as exc:
        return {"status": "error", "detail": str(exc)}
    if _is_stubbed(connector):
        return {"status": "stubbed", "detail": "Vision connector is stubbed"}

    if isinstance(connector, VisionClient):
        try:
            payload = connector.ping()
        except (VisionConfigurationError, VisionError) as exc:
            return {"status": "error", "detail": str(exc)}
        return {"status": "connected", "detail": "Vision connector available", "payload": payload}

    return {"status": "unknown", "detail": "Vision connector unavailable"}
