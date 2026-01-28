"""Google Drive connector for hydration."""

from __future__ import annotations

import io
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from backend.hydration.connectors.base import BaseConnector
from backend.services.google_drive import get_drive_service, drive_stubbed

logger = logging.getLogger(__name__)


class GoogleDriveConnector(BaseConnector):
    """Connector for Google Drive changes API."""

    def validate_config(self) -> None:
        root_id = self.config.get("root_folder_id")
        if not root_id:
            raise ValueError("Google Drive connector requires root_folder_id")

    def list_changes(self, cursor_json: Optional[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        if drive_stubbed():
            logger.info("Google Drive stubbed; returning empty changes")
            return [], cursor_json or {"token": "stub"}

        service = get_drive_service()
        token = (cursor_json or {}).get("token")

        if token:
            return self._list_changes(service, token)

        start_token = service.changes().getStartPageToken().execute()
        token = start_token.get("startPageToken")
        if not token:
            return [], cursor_json or {}

        changes, new_cursor = self._list_changes(service, token)
        return changes, new_cursor

    def _list_changes(self, service: Any, token: str) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        response = (
            service.changes()
            .list(pageToken=token, fields="nextPageToken,newStartPageToken,changes(fileId,file(name,mimeType,modifiedTime,size,md5Checksum,trashed,parents),removed)")
            .execute()
        )
        changes = response.get("changes", [])
        new_token = response.get("newStartPageToken") or response.get("nextPageToken") or token
        items: List[Dict[str, Any]] = []
        for change in changes:
            file_data = change.get("file") or {}
            file_id = change.get("fileId") or file_data.get("id")
            items.append({
                "id": file_id,
                "removed": change.get("removed", False) or file_data.get("trashed", False),
                "file": file_data,
            })
        return items, {"token": new_token}

    def get_metadata(self, item: Dict[str, Any]) -> Dict[str, Any]:
        file_data = item.get("file", {})
        modified = file_data.get("modifiedTime")
        modified_dt = datetime.fromisoformat(modified.replace("Z", "+00:00")) if modified else None
        return {
            "source_document_id": item.get("id") or file_data.get("id"),
            "name": file_data.get("name"),
            "mime_type": file_data.get("mimeType"),
            "modified_time": modified_dt,
            "size_bytes": int(file_data.get("size")) if file_data.get("size") else None,
            "checksum": file_data.get("md5Checksum"),
            "path": f"drive://{item.get('id') or file_data.get('id')}",
            "removed": item.get("removed", False),
        }

    def download(self, item: Dict[str, Any]) -> bytes:
        if drive_stubbed():
            return b""
        service = get_drive_service()
        file_data = item.get("file", {})
        file_id = item.get("id") or file_data.get("id")
        mime_type = file_data.get("mimeType")

        if mime_type and mime_type.startswith("application/vnd.google-apps"):
            export_mime = "text/plain" if "document" in mime_type else "application/pdf"
            request = service.files().export(fileId=file_id, mimeType=export_mime)
        else:
            request = service.files().get_media(fileId=file_id)

        buffer = io.BytesIO()
        downloader = getattr(request, "execute", None)
        if callable(downloader):
            data = request.execute()
            if isinstance(data, bytes):
                return data
            return bytes(data)

        # Fallback if using MediaIoBaseDownload
        from googleapiclient.http import MediaIoBaseDownload  # type: ignore
        downloader = MediaIoBaseDownload(buffer, request)
        done = False
        while not done:
            _, done = downloader.next_chunk()
        return buffer.getvalue()
