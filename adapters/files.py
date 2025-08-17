# adapters/files.py
# Minimal DEMO-only adapters so the app boots on Render.
# Later we’ll replace these with real Google Drive API calls.

import os
from typing import List, Dict

# Fake in-memory file list for the demo
MOCK_FILES: List[Dict] = [
    {"id": "a1", "name": "Project_Schedule.xlsx", "mimeType": "application/vnd.ms-excel", "folder_id": "root"},
    {"id": "a2", "name": "Safety_Report.pdf",     "mimeType": "application/pdf",         "folder_id": "root"},
    {"id": "a3", "name": "Site_Progress.jpg",     "mimeType": "image/jpeg",              "folder_id": "root"},
    {"id": "b1", "name": "Opera_House_Drawings.dwg", "mimeType": "application/octet-stream", "folder_id": "opera"},
    {"id": "b2", "name": "Opera_Structural_Spec.pdf", "mimeType": "application/pdf",         "folder_id": "opera"},
]

DEFAULT_FOLDER_ID = os.getenv("GOOGLE_DRIVE_FOLDER_ID", "root")

def _normalize(s: str) -> str:
    return (s or "").strip().lower()

def fetch_recent_files(limit: int = 10) -> List[Dict]:
    """
    Return latest files (demo data).
    """
    return MOCK_FILES[:limit]

def search_files(query: str, limit: int = 20) -> List[Dict]:
    """
    Search across all files by name (demo search).
    """
    q = _normalize(query)
    if not q:
        return fetch_recent_files(limit)
    hits = [f for f in MOCK_FILES if q in _normalize(f["name"])]
    return hits[:limit]

def search_files_in_folder(folder_id: str, query: str, limit: int = 20) -> List[Dict]:
    """
    Search inside a specific folder (demo search).
    """
    folder = folder_id or DEFAULT_FOLDER_ID
    q = _normalize(query)
    subset = [f for f in MOCK_FILES if f.get("folder_id") == folder]
    if not q:
        return subset[:limit]
    hits = [f for f in subset if q in _normalize(f["name"])]
    return hits[:limit]
