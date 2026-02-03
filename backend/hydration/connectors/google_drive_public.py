"""Google Drive public connector for hydration."""

from __future__ import annotations

import logging
import os
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import requests

from backend.hydration.connectors.base import BaseConnector

logger = logging.getLogger(__name__)

_DRIVE_FILES_URL = "https://www.googleapis.com/drive/v3/files"


class GoogleDrivePublicConnector(BaseConnector):
    """Connector for publicly shared Google Drive folders."""

    def validate_config(self) -> None:
        folder_id = self.config.get("folder_id") or self.config.get("root_folder_id")
        if not folder_id:
            raise ValueError("Google Drive public connector requires folder_id")
        if not self._api_key():
            raise ValueError("GDRIVE_PUBLIC_API_KEY is required for Google Drive public access")

    def list_changes(self, cursor_json: Optional[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        folder_id = self.config.get("folder_id") or self.config.get("root_folder_id")
        api_key = self._api_key()
        timeout = self._timeout_seconds()

        page_token = (cursor_json or {}).get("page_token")
        page_size = self._page_size()
        logger.debug(
            "Listing public Drive files folder_id=%s page_size=%s page_token=%s",
            folder_id,
            page_size,
            page_token,
        )

        items: List[Dict[str, Any]] = []
        next_token = page_token
        while True:
            params = {
                "key": api_key,
                "q": f"'{folder_id}' in parents and trashed=false",
                "fields": "nextPageToken,files(id,name,mimeType,modifiedTime,size,md5Checksum)",
                "pageSize": page_size,
                "includeItemsFromAllDrives": "true",
                "supportsAllDrives": "true",
                "orderBy": "modifiedTime desc",
            }
            if next_token:
                params["pageToken"] = next_token

            response = requests.get(_DRIVE_FILES_URL, params=params, timeout=timeout)
            response.raise_for_status()
            payload = response.json()
            files = payload.get("files", [])
            for file_data in files:
                items.append({
                    "id": file_data.get("id"),
                    "removed": False,
                    "file": file_data,
                })

            next_token = payload.get("nextPageToken")
            if not next_token:
                break
            logger.debug("Continuing public Drive pagination next_token=%s", next_token)

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
