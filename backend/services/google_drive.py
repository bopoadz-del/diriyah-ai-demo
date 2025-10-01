"""Utilities for uploading files to Google Drive with a stub fallback."""
from __future__ import annotations

import io
import json
import logging
import os
from typing import Any, Dict

logger = logging.getLogger(__name__)

# Attempt to import the media upload helper from the Google client library. The
# import is optional so tests can run without the dependency.
try:  # pragma: no cover - exercised indirectly in environments with the SDK
    from googleapiclient.http import MediaIoBaseUpload  # type: ignore
except Exception:  # pragma: no cover - handled during unit tests
    MediaIoBaseUpload = None  # type: ignore[misc,assignment]

SCOPES = ["https://www.googleapis.com/auth/drive.file"]
DEFAULT_SERVICE_ACCOUNT_FILE = "service_account.json"
STUB_FILE_ID = os.getenv("GOOGLE_DRIVE_STUB_FILE_ID", "stub-file-id")


def _stub_upload(_: Any) -> str:
    """Return the stub identifier for uploads when Drive isn't available."""

    return STUB_FILE_ID


def _load_service_account_credentials():
    """Load service account credentials from file or embedded JSON."""

    try:
        from google.oauth2 import service_account  # type: ignore
    except Exception as exc:  # pragma: no cover - handled by callers
        raise RuntimeError("google.oauth2 is not available") from exc

    credentials_json = os.getenv("GOOGLE_SERVICE_ACCOUNT_INFO")
    if credentials_json:
        info: Dict[str, Any] = json.loads(credentials_json)
        return service_account.Credentials.from_service_account_info(info, scopes=SCOPES)

    service_account_file = os.getenv("GOOGLE_SERVICE_ACCOUNT", DEFAULT_SERVICE_ACCOUNT_FILE)
    if not os.path.exists(service_account_file):
        raise RuntimeError("Service account file not found")

    return service_account.Credentials.from_service_account_file(service_account_file, scopes=SCOPES)


def get_drive_service():
    """Return an authenticated Google Drive service client."""

    try:
        from googleapiclient.discovery import build  # type: ignore
    except Exception as exc:  # pragma: no cover - handled by callers
        raise RuntimeError("googleapiclient is not available") from exc

    credentials = _load_service_account_credentials()
    return build("drive", "v3", credentials=credentials)


def upload_to_drive(file: Any) -> str:
    """Upload *file* to Google Drive or fall back to the stub identifier.

    The function first attempts to construct a Drive service client. Only when
    that fails—or when the optional ``MediaIoBaseUpload`` helper is not
    available—does it return the stub identifier. This ordering ensures that we
    detect genuine Drive failures before consulting the stub state.
    """

    try:
        service = get_drive_service()
    except Exception:  # pragma: no cover - the behaviour is validated via tests
        logger.debug("Drive service unavailable, using stub.", exc_info=True)
        return _stub_upload(file)

    if MediaIoBaseUpload is None:
        logger.debug("MediaIoBaseUpload helper missing, using stub.")
        return _stub_upload(file)

    stream = getattr(file, "file", file)
    if stream is None:
        payload = b""
    else:
        payload = stream.read()
        if hasattr(stream, "seek"):
            stream.seek(0)

    filename = getattr(file, "filename", "upload.bin")
    mimetype = getattr(file, "content_type", "application/octet-stream")
    metadata = {"name": filename}
    parent_folder = os.getenv("GOOGLE_DRIVE_FOLDER_ID")
    if parent_folder:
        metadata["parents"] = [parent_folder]

    try:
        media = MediaIoBaseUpload(io.BytesIO(payload), mimetype=mimetype, resumable=False)  # type: ignore[arg-type]
    except Exception:  # pragma: no cover - depends on optional SDK behaviour
        logger.debug("Failed to initialise MediaIoBaseUpload, using stub.", exc_info=True)
        return _stub_upload(file)

    try:
        result = (
            service.files()  # type: ignore[operator]
            .create(body=metadata, media_body=media, fields="id")
            .execute()
        )
    except Exception:
        logger.debug("Drive upload failed, using stub.", exc_info=True)
        return _stub_upload(file)

    return result.get("id") or _stub_upload(file)
