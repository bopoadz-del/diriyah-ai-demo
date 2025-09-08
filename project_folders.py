import os, json
from typing import Optional, Dict

PATH = os.getenv("PROJECT_FOLDER_STORE","./project_folders.json")

def _load() -> Dict[str, dict]:
    if not os.path.exists(PATH): return {}
    try:
        with open(PATH,"r",encoding="utf-8") as f: return json.load(f)
    except Exception: return {}

def _save(d: Dict[str,dict]):
    with open(PATH,"w",encoding="utf-8") as f: json.dump(d,f,indent=2)

def upsert_mapping(project_name: str, provider: str, folder_id: str, display_name: str|None=None):
    d = _load()
    d[project_name.lower()] = {
        "project_name": project_name,
        "provider": provider,
        "folder_id": folder_id,
        "display_name": display_name or project_name
    }
    _save(d)

def get_mapping(project_name: str) -> Optional[dict]:
    return _load().get(project_name.lower())

def list_mappings() -> Dict[str,dict]:
    return _load()

def delete_mapping(project_name: str):
    d = _load(); d.pop(project_name.lower(), None); _save(d)
