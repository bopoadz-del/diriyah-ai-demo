from __future__ import annotations

from typing import Any, Dict, List

from .drive_service import download_file
from .qto_pipeline import parse_dwg


class CADTakeoffService:
    """Generate lightweight take-off insights backed by Google Drive files."""

    def process_dwg(self, file_id: str) -> Dict[str, Any]:
        local_path = download_file(file_id, extension=".dwg")
        try:
            entities: List[Dict[str, Any]] = parse_dwg(local_path)
            status = "ok"
        except Exception as exc:
            entities = [
                {
                    "type": "stub",
                    "layer": "N/A",
                    "note": "Fell back to stubbed geometry while Drive uses demo data.",
                    "error": str(exc),
                }
            ]
            status = "stubbed"

        return {
            "status": status,
            "file_id": file_id,
            "local_path": local_path,
            "entities": entities,
        }
