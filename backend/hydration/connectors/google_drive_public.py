"""Google Drive public connector for hydration."""

from __future__ import annotations

import io
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from backend.hydration.connectors.base import BaseConnector
from backend.services.google_drive import drive_stubbed, get_drive_service

logger = logging.getLogger(__name__)


class GoogleDrivePublicConnector(BaseConnector):
    """Connector for publicly shared Google Drive folders."""

    def validate_config(self) -> None:
        folder_id = self.config.get("folder_id") or self.config.get("root_folder_id")
        if not folder_id:
            raise ValueError("Google Drive public connector requires folder_id")

    def list_changes(self, cursor_json: Optional[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        if drive_stubbed():
            logger.info("Google Drive stubbed; returning empty changes")
            return [], cursor_json or {}

        folder_id = self.config.get("folder_id") or self.config.get("root_folder_id")
        service = get_drive_service()
        page_token = (cursor_json or {}).get("page_token")
        response = (
            service.files()
            .list(
                q=f"'{folder_id}' in parents and trashed=false",
                fields="nextPageToken,files(id,name,mimeType,modifiedTime,size,md5Checksum,trashed,parents)",
                pageSize=200,
                pageToken=page_token,
            )
            .execute()
        )
        files = response.get("files", [])
        items: List[Dict[str, Any]] = []
        for file_data in files:
            items.append({
                "id": file_data.get("id"),
                "removed": file_data.get("trashed", False),
                "file": file_data,
            })

        next_token = response.get("nextPageToken")
        return items, {"page_token": next_token} if next_token else {}

    def get_metadata(self, item: Dict[str, Any]) -> Dict[str, Any]:
        file_data = item.get("file", {})
        name = file_data.get("name")
        mime_type = file_data.get("mimeType")
        if mime_type and mime_type.startswith("application/vnd.google-apps"):
            mime_type = "application/pdf"
            if name and not name.lower().endswith(".pdf"):
                name = f"{name}.pdf"

        modified = file_data.get("modifiedTime")
        modified_dt = datetime.fromisoformat(modified.replace("Z", "+00:00")) if modified else None
        return {
            "source_document_id": item.get("id") or file_data.get("id"),
            "name": name,
            "mime_type": mime_type,
            "modified_time": modified_dt,
            "size_bytes": int(file_data.get("size")) if file_data.get("size") else None,
            "checksum": file_data.get("md5Checksum"),
            "path": f"drive-public://{item.get('id') or file_data.get('id')}",
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
            request = service.files().export(fileId=file_id, mimeType="application/pdf")
        else:
            request = service.files().get_media(fileId=file_id)

        buffer = io.BytesIO()
        downloader = getattr(request, "execute", None)
        if callable(downloader):
            data = request.execute()
            if isinstance(data, bytes):
                return data
            return bytes(data)

        from googleapiclient.http import MediaIoBaseDownload  # type: ignore

        downloader = MediaIoBaseDownload(buffer, request)
        done = False
        while not done:
            _, done = downloader.next_chunk()
        return buffer.getvalue()


__all__ = ["GoogleDrivePublicConnector"]
