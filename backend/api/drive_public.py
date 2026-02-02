"""Public Google Drive list endpoints for demo ingestion."""

from __future__ import annotations

import logging
from typing import Any, Dict, List

from fastapi import APIRouter, HTTPException, Query

from backend.hydration.connectors.google_drive_public import GoogleDrivePublicConnector
from backend.services.google_drive import drive_stubbed

router = APIRouter(prefix="/drive/public")
logger = logging.getLogger(__name__)


def _serialize_metadata(metadata: Dict[str, Any]) -> Dict[str, Any]:
    payload = dict(metadata)
    modified = payload.get("modified_time")
    if modified is not None:
        payload["modified_time"] = modified.isoformat()
    return payload


@router.get("/list")
def list_drive_public_files(
    folder_id: str = Query(...),
    page_size: int = Query(200, ge=1, le=1000),
    max_pages: int = Query(10, ge=1, le=100),
) -> Dict[str, List[Dict[str, Any]]]:
    """List files in a public Drive folder."""

    if drive_stubbed():
        return {"files": [], "status": "stubbed"}

    if not GoogleDrivePublicConnector.is_valid_folder_id(folder_id):
        raise HTTPException(status_code=400, detail="Invalid folder id")

    connector = GoogleDrivePublicConnector(
        {
            "folder_id": folder_id,
            "page_size": page_size,
        }
    )
    try:
        connector.validate_config()
        items: List[Dict[str, Any]] = []
        cursor: Dict[str, Any] = {}
        page_count = 0
        while True:
            page_items, cursor = connector.list_changes(cursor)
            items.extend(page_items)
            page_count += 1
            page_token = cursor.get("page_token")
            if not page_token:
                break
            if page_count >= max_pages:
                logger.warning(
                    "Drive public listing stopped after max pages",
                    extra={"folder_id": folder_id, "page_count": page_count},
                )
                break
        files = [_serialize_metadata(connector.get_metadata(item)) for item in items]
    except ValueError as exc:
        logger.info("Rejected invalid Drive folder id", extra={"folder_id": folder_id})
        raise HTTPException(status_code=400, detail="Invalid folder id") from exc
    except Exception as exc:  # pragma: no cover - defensive API guard
        logger.exception("Drive public listing failed")
        raise HTTPException(status_code=500, detail="Internal server error") from exc

    return {"files": files, "status": "ok"}


__all__ = ["router"]
