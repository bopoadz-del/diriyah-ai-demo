"""Google Drive helper functions with graceful stub fallbacks."""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List, Optional

logger = logging.getLogger(__name__)

__all__ = (
    "drive_credentials_available",
    "drive_service_error",
    "get_drive_service",
    "get_project",
    "list_project_folders",
    "upload_to_drive",
)

if TYPE_CHECKING:  # pragma: no cover - hinting only
    from fastapi import UploadFile
else:  # pragma: no cover - runtime fallback when FastAPI not available
    UploadFile = Any  # type: ignore[misc,assignment]

DRIVE_SCOPE = "https://www.googleapis.com/auth/drive"

STUB_FILE_ID = "stub-file-0001"
STUB_FOLDERS: List[Dict[str, str]] = [
    {
        "id": "stub-folder-001",
        "name": "Gateway District Phase 1",
        "mimeType": "application/vnd.google-apps.folder",
    },
    {
        "id": "stub-folder-002",
        "name": "Bujairi Terrace Expansion",
        "mimeType": "application/vnd.google-apps.folder",
    },
]

_last_service_error: Optional[str] = None
_last_service_error_source: Optional[str] = None


def _credentials_path(*, record_errors: bool = False) -> Optional[Path]:
    """Return the credentials path if the environment is configured."""

    env_value = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
    if not env_value:
        if record_errors:
            _record_service_error("GOOGLE_APPLICATION_CREDENTIALS is not set", source="credentials")
        return None

    candidate = Path(env_value).expanduser()

    if not candidate.exists():
        if record_errors:
            _record_service_error(f"Credentials file not found: {candidate}", source="credentials")
        return None

    if not candidate.is_file():
        if record_errors:
            _record_service_error(f"Credentials path is not a file: {candidate}", source="credentials")
        return None

    if not os.access(candidate, os.R_OK):
        if record_errors:
            _record_service_error(f"Credentials file is not readable: {candidate}", source="credentials")
        return None

    if record_errors and _last_service_error_source == "credentials":
        _record_service_error(None)

    return candidate


def drive_credentials_available() -> bool:
    """Return ``True`` when credentials exist and are readable."""

    return _credentials_path(record_errors=True) is not None


def drive_service_error() -> Optional[str]:
    """Return the last recorded service error, if any."""

    return _last_service_error


def _record_service_error(reason: Optional[str], *, source: str = "service") -> None:
    global _last_service_error, _last_service_error_source
    _last_service_error = reason
    _last_service_error_source = source if reason is not None else None


def get_drive_service() -> Any | None:
    """Return a Google Drive service or ``None`` when unavailable."""

    credentials_path = _credentials_path(record_errors=True)
    if not credentials_path:
        return None

    try:
        from google.oauth2 import service_account  # type: ignore
        from googleapiclient.discovery import build  # type: ignore
    except Exception as exc:  # pragma: no cover - requires optional dependency
        logger.warning("Google Drive libraries unavailable: %s", exc)
        _record_service_error(str(exc), source="initialisation")
        return None

    try:
        credentials = service_account.Credentials.from_service_account_file(
            str(credentials_path), scopes=[DRIVE_SCOPE]
        )
        service = build("drive", "v3", credentials=credentials, cache_discovery=False)
        _record_service_error(None)
        return service
    except Exception as exc:  # pragma: no cover - defensive, depends on Google client
        logger.warning("Failed to initialise Google Drive service: %s", exc)
        _record_service_error(str(exc), source="initialisation")
        return None


def upload_to_drive(
    file_obj: "UploadFile",
    *,
    service: Any | None = None,
    lookup_service: bool = True,
) -> str:
    """Upload a file to Drive or return a deterministic stub identifier."""

    if service is None and lookup_service:
        service = get_drive_service()
    if service is None:
        return STUB_FILE_ID

    try:  # pragma: no cover - exercised only with Google client available
        from googleapiclient.http import MediaIoBaseUpload  # type: ignore

        metadata = {"name": getattr(file_obj, "filename", "upload.bin")}
        media = MediaIoBaseUpload(
            file_obj.file, mimetype=getattr(file_obj, "content_type", None), resumable=False
        )
        response = (
            service.files()
            .create(body=metadata, media_body=media, fields="id")
            .execute()
        )
        return response.get("id", STUB_FILE_ID)
    except Exception as exc:
        logger.warning("Drive upload failed, returning stub identifier: %s", exc)
        return STUB_FILE_ID


def list_project_folders(
    *, service: Any | None = None, lookup_service: bool = True
) -> List[Dict[str, Any]]:
    """List project folders from Drive or return stub fixtures."""

    if service is None and lookup_service:
        service = get_drive_service()
    if service is None:
        return [folder.copy() for folder in STUB_FOLDERS]

    try:  # pragma: no cover - exercised only with Google client available
        response = (
            service.files()
            .list(
                q="mimeType='application/vnd.google-apps.folder' and trashed=false",
                fields="files(id,name,mimeType)",
            )
            .execute()
        )
        return response.get("files", [])
    except Exception as exc:
        logger.warning("Drive list failed, returning stub folders: %s", exc)
        return list(STUB_FOLDERS)


def get_project(project_id: str) -> Dict[str, str]:
    """Return stub project metadata."""

    return {
        "id": project_id,
        "name": f"Project {project_id}",
        "drive_id": "stub",
    }
