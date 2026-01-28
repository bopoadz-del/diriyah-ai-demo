"""Server filesystem connector."""

from __future__ import annotations

import fnmatch
import hashlib
import os
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional, Tuple

from backend.hydration.connectors.base import BaseConnector


class ServerFSConnector(BaseConnector):
    """Connector for server filesystem sources."""

    def validate_config(self) -> None:
        root_path = self.config.get("root_path")
        if not root_path:
            raise ValueError("Server FS connector requires root_path")
        if not os.path.isdir(root_path):
            raise ValueError(f"Server FS root_path not found: {root_path}")

    def list_changes(self, cursor_json: Optional[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        root_path = self.config.get("root_path")
        include_patterns = self.config.get("include", ["*"])
        exclude_patterns = self.config.get("exclude", [])
        last_scan = cursor_json.get("last_scan_time") if cursor_json else None
        last_scan_dt = datetime.fromisoformat(last_scan) if last_scan else None

        items: List[Dict[str, Any]] = []
        for path in self._iter_files(root_path, include_patterns, exclude_patterns):
            stat = os.stat(path)
            mtime = datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc)
            if last_scan_dt and mtime <= last_scan_dt and stat.st_size >= 0:
                continue
            items.append({
                "path": path,
                "size": stat.st_size,
                "modified_time": mtime,
            })

        cursor = {"last_scan_time": datetime.now(tz=timezone.utc).isoformat()}
        return items, cursor

    def _iter_files(self, root_path: str, include_patterns: Iterable[str], exclude_patterns: Iterable[str]) -> Iterable[str]:
        for dirpath, dirnames, filenames in os.walk(root_path, followlinks=False):
            dirnames[:] = [d for d in dirnames if not os.path.islink(os.path.join(dirpath, d))]
            for filename in filenames:
                if not self._matches_patterns(filename, include_patterns, exclude_patterns):
                    continue
                yield os.path.join(dirpath, filename)

    def _matches_patterns(self, name: str, include_patterns: Iterable[str], exclude_patterns: Iterable[str]) -> bool:
        included = any(fnmatch.fnmatch(name, pattern) for pattern in include_patterns)
        if not included:
            return False
        if any(fnmatch.fnmatch(name, pattern) for pattern in exclude_patterns):
            return False
        return True

    def get_metadata(self, item: Dict[str, Any]) -> Dict[str, Any]:
        path = item["path"]
        checksum = self._checksum(path)
        return {
            "source_document_id": checksum,
            "name": os.path.basename(path),
            "mime_type": None,
            "modified_time": item.get("modified_time"),
            "size_bytes": item.get("size"),
            "checksum": checksum,
            "path": path,
            "removed": False,
        }

    def download(self, item: Dict[str, Any]) -> bytes:
        with open(item["path"], "rb") as handle:
            return handle.read()

    def _checksum(self, path: str) -> str:
        hasher = hashlib.md5()
        with open(path, "rb") as handle:
            for chunk in iter(lambda: handle.read(8192), b""):
                hasher.update(chunk)
        return hasher.hexdigest()
