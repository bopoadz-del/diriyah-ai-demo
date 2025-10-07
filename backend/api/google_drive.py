"""Lightweight Google Drive endpoints for demo integrations."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from backend.services.drive_service import list_files, upload_file

router = APIRouter()


@router.get("/drive/list")
def list_drive_files() -> dict[str, object]:
    """Return Drive folders used to seed demo project pickers."""

    try:
        files = list_files()
    except Exception as exc:  # pragma: no cover - defensive API guard
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return {"status": "ok", "files": files}


@router.post("/drive/upload")
def upload_drive_file(file_path: str) -> dict[str, str]:
    """Upload a file by path so demos can simulate Drive ingestion flows."""

    try:
        file_id = upload_file(file_path)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:  # pragma: no cover - defensive API guard
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return {"status": "ok", "file_id": file_id}


__all__ = ["router"]
