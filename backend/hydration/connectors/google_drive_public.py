"""Google Drive public connector for hydration."""

from __future__ import annotations

import logging
import re
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import requests

from backend.hydration.connectors.base import BaseConnector

logger = logging.getLogger(__name__)

_DRIVE_FILES_URL = "https://www.googleapis.com/drive/v3/files"


class GoogleDrivePublicConnector(BaseConnector):
    """Connector for publicly shared Google Drive folders."""

    _FOLDER_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]{10,200}$")

    @classmethod
    def is_valid_folder_id(cls, folder_id: Optional[str]) -> bool:
        if not folder_id:
            return False
        return bool(cls._FOLDER_ID_PATTERN.fullmatch(folder_id))

    def validate_config(self) -> None:
        folder_id = self.config.get("folder_id") or self.config.get("root_folder_id")
        if not self.is_valid_folder_id(folder_id):
            raise ValueError("Invalid Google Drive folder id")

    def list_changes(self, cursor_json: Optional[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        folder_id = self.config.get("folder_id") or self.config.get("root_folder_id")
        service = get_drive_service()
        items: List[Dict[str, Any]] = []
        page_token = (cursor_json or {}).get("page_token")
        page_size = self.config.get("page_size", 200)
        try:
            page_size = int(page_size)
        except (TypeError, ValueError):
            page_size = 200
        page_size = max(1, min(page_size, 1000))
        logger.debug("Listing Google Drive files with page_size=%s page_token=%s", page_size, page_token)

        next_token = page_token
        while True:
            response = (
                service.files()
                .list(
                    q=f"'{folder_id}' in parents and trashed=false",
                    fields="nextPageToken,files(id,name,mimeType,modifiedTime,size,md5Checksum,trashed,parents)",
                    pageSize=page_size,
                    pageToken=next_token,
                )
                .execute()
            )
            files = response.get("files", [])
            for file_data in files:
                items.append({
                    "id": file_data.get("id"),
                    "removed": file_data.get("trashed", False),
                    "file": file_data,
                })
            next_token = response.get("nextPageToken")
            if not next_token:
                break
            logger.debug("Google Drive pagination continuing with next_token=%s", next_token)

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
        checksum = file_data.get("md5Checksum") or modified
        return {
            "source_document_id": item.get("id") or file_data.get("id"),
            "name": name,
            "mime_type": mime_type,
            "modified_time": modified_dt,
            "size_bytes": int(file_data.get("size")) if file_data.get("size") else None,
            "checksum": checksum,
            "path": f"drive-public://{item.get('id') or file_data.get('id')}",
            "removed": item.get("removed", False),
        }

    def download(self, item: Dict[str, Any]) -> bytes:
        file_data = item.get("file", {})
        file_id = item.get("id") or file_data.get("id")
        mime_type = file_data.get("mimeType")
        api_key = self._api_key()
        timeout = self._timeout_seconds()

        if not file_id:
            raise ValueError("Missing file id for Google Drive public download")

        if mime_type and mime_type.startswith("application/vnd.google-apps"):
            url = f"{_DRIVE_FILES_URL}/{file_id}/export"
            params = {"key": api_key, "mimeType": "application/pdf"}
        else:
            url = f"{_DRIVE_FILES_URL}/{file_id}"
            params = {"key": api_key, "alt": "media"}

        response = requests.get(url, params=params, timeout=timeout)
        response.raise_for_status()
        return response.content

    def _api_key(self) -> str:
        return os.getenv("GDRIVE_PUBLIC_API_KEY", "")

    def _timeout_seconds(self) -> float:
        raw_timeout = os.getenv("GDRIVE_PUBLIC_TIMEOUT_SECONDS", "60")
        try:
            timeout_value = float(raw_timeout)
        except (TypeError, ValueError):
            timeout_value = 60.0
        return max(1.0, timeout_value)

    def _page_size(self) -> int:
        page_size = self.config.get("page_size", 1000)
        try:
            page_size_value = int(page_size)
        except (TypeError, ValueError):
            page_size_value = 1000
        return max(1, min(page_size_value, 1000))


__all__ = ["GoogleDrivePublicConnector"]
