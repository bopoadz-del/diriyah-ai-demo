"""Public Google Drive list endpoints for demo ingestion."""

from __future__ import annotations

from typing import Any, Dict, List

from fastapi import APIRouter, HTTPException, Query

from backend.hydration.connectors.google_drive_public import GoogleDrivePublicConnector
from backend.services.google_drive import drive_stubbed

router = APIRouter(prefix="/drive/public")


def _serialize_metadata(metadata: Dict[str, Any]) -> Dict[str, Any]:
    payload = dict(metadata)
    modified = payload.get("modified_time")
    if modified is not None:
        payload["modified_time"] = modified.isoformat()
    return payload


@router.get("/list")
def list_drive_public_files(folder_id: str = Query(...)) -> Dict[str, List[Dict[str, Any]]]:
    """List files in a public Drive folder."""

    if drive_stubbed():
        return {"files": [], "status": "stubbed"}

    connector = GoogleDrivePublicConnector({"folder_id": folder_id})
    try:
        connector.validate_config()
        items, _ = connector.list_changes({})
        files = [_serialize_metadata(connector.get_metadata(item)) for item in items]
    except Exception as exc:  # pragma: no cover - defensive API guard
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return {"files": files, "status": "ok"}


__all__ = ["router"]
