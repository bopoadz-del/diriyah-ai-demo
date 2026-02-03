"""Public Google Drive list + ingest endpoints."""

from __future__ import annotations

import json
import logging
import os
import uuid
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.backend.db import get_db
from backend.hydration.connectors.google_drive_public import GoogleDrivePublicConnector
from backend.hydration.models import SourceType, WorkspaceSource
from backend.redisx.queue import RedisQueue

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/drive/public", tags=["Drive Public"])


class DrivePublicIngestRequest(BaseModel):
    workspace_id: str
    folder_id: str
    dry_run: bool = False
    force_full_scan: bool = False
    max_files: Optional[int] = None


def _serialize_file_data(file_data: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "id": file_data.get("id"),
        "name": file_data.get("name"),
        "mimeType": file_data.get("mimeType"),
        "modifiedTime": file_data.get("modifiedTime"),
        "size": file_data.get("size"),
    }


def _upsert_public_source(db: Session, workspace_id: str, folder_id: str) -> WorkspaceSource:
    existing_sources = (
        db.query(WorkspaceSource)
        .filter(
            WorkspaceSource.workspace_id == workspace_id,
            WorkspaceSource.source_type == SourceType.GOOGLE_DRIVE_PUBLIC,
        )
        .all()
    )

    target_source = None
    for source in existing_sources:
        try:
            config = json.loads(source.config_json or "{}")
        except json.JSONDecodeError:
            config = {}
        if config.get("folder_id") == folder_id:
            target_source = source
            break

    name = f"GDrive Public {folder_id}"
    config_json = json.dumps({"folder_id": folder_id})
    if target_source:
        target_source.name = name
        target_source.config_json = config_json
        target_source.is_enabled = True
        db.commit()
        db.refresh(target_source)
        return target_source

    source = WorkspaceSource(
        workspace_id=workspace_id,
        source_type=SourceType.GOOGLE_DRIVE_PUBLIC,
        name=name,
        config_json=config_json,
        is_enabled=True,
    )
    db.add(source)
    db.commit()
    db.refresh(source)
    return source


@router.get("/list")
def list_drive_public_files(
    folder_id: str = Query(...),
    page_token: Optional[str] = Query(default=None),
) -> Dict[str, Any]:
    """List files in a public Drive folder."""

    connector = GoogleDrivePublicConnector({"folder_id": folder_id})
    try:
        connector.validate_config()
        items, cursor = connector.list_changes({"page_token": page_token} if page_token else {})
        files = [_serialize_file_data(item.get("file", {})) for item in items]
    except Exception as exc:  # pragma: no cover - defensive API guard
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return {"files": files, "next_page_token": cursor.get("page_token")}


@router.post("/ingest", status_code=status.HTTP_202_ACCEPTED)
def ingest_drive_public_files(
    payload: DrivePublicIngestRequest,
    db: Session = Depends(get_db),
    x_correlation_id: Optional[str] = Header(default=None, alias="X-Correlation-Id"),
) -> Dict[str, Any]:
    """Upsert a public Drive source and enqueue a hydration run."""

    try:
        source = _upsert_public_source(db, payload.workspace_id, payload.folder_id)

        queue = RedisQueue()
        correlation_id = x_correlation_id or os.getenv("CORRELATION_ID") or str(uuid.uuid4())
        job_payload = {
            "workspace_id": payload.workspace_id,
            "source_ids": [source.id],
            "force_full_scan": payload.force_full_scan,
            "max_files": payload.max_files,
            "dry_run": payload.dry_run,
        }
        headers = {"correlation_id": correlation_id, "workspace_id": payload.workspace_id}
        job_id = queue.enqueue("hydration", job_payload, headers, db=db)
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Failed to enqueue public Drive hydration: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return {"job_id": job_id, "source_id": source.id, "status": "queued"}


__all__ = ["router"]
