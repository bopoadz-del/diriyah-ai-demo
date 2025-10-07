"""Compatibility wrappers for Google Drive workflows used by demo services."""

from __future__ import annotations

import mimetypes
import tempfile
from pathlib import Path
from typing import Any, Dict, Iterable, List

from . import google_drive

try:  # pragma: no cover - exercised indirectly when googleapiclient is installed
    from googleapiclient.http import MediaIoBaseDownload  # type: ignore
except Exception:  # pragma: no cover - environments without googleapiclient
    MediaIoBaseDownload = None  # type: ignore[assignment]


def list_files() -> List[Dict[str, Any]]:
    """Expose project folders to legacy callers that expect a list endpoint."""

    folders = google_drive.list_project_folders()
    if isinstance(folders, Iterable):
        return list(folders)
    return []


class _UploadShim:
    """Minimal adapter so the Drive helper accepts a filesystem path."""

    def __init__(self, path: Path) -> None:
        self._path = path
        self.file = path.open("rb")
        self.filename = path.name
        guessed, _ = mimetypes.guess_type(path.name)
        self.content_type = guessed or "application/octet-stream"

    def close(self) -> None:
        try:
            self.file.close()
        except Exception:
            pass


def upload_file(file_path: str) -> str:
    """Upload ``file_path`` to Drive or return a stub identifier when offline."""

    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"File does not exist: {path}")

    shim = _UploadShim(path)
    try:
        return google_drive.upload_to_drive(shim)
    finally:
        shim.close()


def _write_stub(file_id: str, *, extension: str | None = None) -> str:
    """Persist a lightweight placeholder file so downstream parsers can run."""

    suffix = extension or ".txt"
    with tempfile.NamedTemporaryFile("w", delete=False, prefix=f"stub-{file_id}-", suffix=suffix) as handle:
        handle.write(f"Stub data for Drive file {file_id}\n")
        return handle.name


def download_file(file_id: str, *, extension: str | None = None) -> str:
    """Download a Drive file for local processing or return a stub path."""

    try:
        service = google_drive.get_drive_service()
    except RuntimeError:
        return _write_stub(file_id, extension=extension)

    if MediaIoBaseDownload is None:
        return _write_stub(file_id, extension=extension)

    request = service.files().get_media(fileId=file_id)
    suffix = extension or ""
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as handle:
            downloader = MediaIoBaseDownload(handle, request)
            done = False
            while not done:
                _, done = downloader.next_chunk()
            handle.flush()
            return handle.name
    except Exception:  # pragma: no cover - defensive network path
        return _write_stub(file_id, extension=extension)


__all__ = ["list_files", "upload_file", "download_file"]
