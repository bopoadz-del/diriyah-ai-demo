# adapters/project_folders.py
from __future__ import annotations
from typing import Dict, List, Optional
import json, os
from threading import Lock

_STORE_PATH = os.environ.get("PROJECT_MAP_STORE", "project_mappings.json")
_LOCK = Lock()

def _load_store() -> Dict[str, Dict]:
    if not os.path.exists(_STORE_PATH):
        return {}
    try:
        with open(_STORE_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def _save_store(data: Dict[str, Dict]) -> None:
    tmp = _STORE_PATH + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp, _STORE_PATH)

def upsert_mapping(project_id: str, provider: str, folder_id: str, folder_name: Optional[str] = None) -> Dict:
    with _LOCK:
        data = _load_store()
        data[str(project_id)] = {
            "project_id": str(project_id),
            "provider": provider,
            "folder_id": folder_id,
            "folder_name": folder_name or "",
        }
        _save_store(data)
        return data[str(project_id)]

def get_mapping(project_id: str) -> Optional[Dict]:
    with _LOCK:
        return _load_store().get(str(project_id))

def list_mappings() -> List[Dict]:
    with _LOCK:
        return list(_load_store().values())

def delete_mapping(project_id: str) -> bool:
    with _LOCK:
        data = _load_store()
        if str(project_id) in data:
            del data[str(project_id)]
            _save_store(data)
            return True
        return False
