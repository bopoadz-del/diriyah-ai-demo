"""
drive_adapter.py
-----------------

This module encapsulates all interactions with Google Drive.  It
supports searching files by keyword within a project folder, extracting
text from PDF and Word documents, caching that content locally and
refreshing it on a schedule.  The assistant queries the cache to
respond quickly while still providing up‑to‑date data via periodic
refreshes.

Assumptions:

* A Google service account JSON key is provided via the
  `GOOGLE_APPLICATION_CREDENTIALS` environment variable and each
  project folder in Drive is shared with the service account.
* Project → folder mapping is loaded from ``projects.json``.

"""

from __future__ import annotations

import io
import os
import re
import json
import threading
import time
from pathlib import Path
from typing import List, Dict, Any, Tuple

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaIoBaseDownload

# Import extractors for non‑Google docs
from .extractors import extract_from_bytes

# Load project folder IDs
PROJECTS_FILE = Path(__file__).parent / "projects.json"
with open(PROJECTS_FILE, "r", encoding="utf-8") as f:
    _PROJECTS = json.load(f)["projects"]

# Directory for cached text
CACHE_ROOT = Path(__file__).parent / "cache"
CACHE_ROOT.mkdir(exist_ok=True)

# Global dictionary to track last refresh timestamps per project
LAST_UPDATE: Dict[str, str] = {}

# Service account credentials
SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]

def ensure_credentials() -> service_account.Credentials | None:
    """Load service account credentials from GOOGLE_APPLICATION_CREDENTIALS."""
    json_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    if not json_path:
        return None
    try:
        creds = service_account.Credentials.from_service_account_file(
            json_path, scopes=SCOPES
        )
        return creds
    except Exception:
        return None

def build_drive_service(creds: service_account.Credentials):
    """Create a Drive API service from credentials."""
    return build("drive", "v3", credentials=creds)

def tokenize(q: str) -> List[str]:
    return [t for t in re.split(r"[^A-Za-z0-9_]+", q.lower()) if len(t) > 2 and t not in {"the", "and", "for", "with", "from", "this", "that"}]

def q_to_drive(q: str) -> str:
    terms = tokenize(q)
    if not terms:
        return "trashed=false"
    inner = " or ".join([f"name contains '{t}' or fullText contains '{t}'" for t in terms[:4]])
    return f"trashed=false and ({inner})"

def search_files(service, q: str, folder_id: str, page_size: int = 20) -> List[Dict[str, Any]]:
    """Search files in a given folder matching the query."""
    base = f"'{folder_id}' in parents and trashed=false"
    try:
        res = service.files().list(
            q=f"{base} and ({q_to_drive(q)})",
            pageSize=page_size,
            fields="files(id,name,mimeType,size,modifiedTime)"
        ).execute()
    except HttpError:
        return []
    return res.get("files", [])

SUPPORTED_EXPORTS: Dict[str, str] = {
    # Google Docs formats exportable to plain text
    "application/vnd.google-apps.document": "text/plain",
    "application/vnd.google-apps.spreadsheet": "text/csv",
    "application/vnd.google-apps.presentation": "text/plain",
}

def download_text(service, file_id: str, mime_type: str) -> str:
    """Download and extract plain text from a Drive file.

    For Google Docs formats, the file is exported to a plain text
    format using the Drive API.  For all other formats, the raw
    bytes are downloaded and passed to the extractor layer.  The
    extractors support PDF, Word, Excel, CSV and generic UTF‑8
    decode.  Unsupported binary formats return an empty string.

    Args:
        service: Drive API service instance.
        file_id: The ID of the file to download.
        mime_type: The MIME type reported by Drive.

    Returns:
        Extracted text or an empty string if extraction fails.
    """
    # Export Google native formats
    if mime_type in SUPPORTED_EXPORTS:
        export = SUPPORTED_EXPORTS[mime_type]
        try:
            data = service.files().export(fileId=file_id, mimeType=export).execute()
            return data.decode("utf-8", errors="ignore")
        except Exception:
            return ""
    # Otherwise download raw bytes
    try:
        req = service.files().get_media(fileId=file_id)
        buf = io.BytesIO()
        downloader = MediaIoBaseDownload(buf, req)
        done = False
        while not done:
            _, done = downloader.next_chunk()
        content = buf.getvalue()
    except Exception:
        return ""
    # Delegate to extractor layer
    return extract_from_bytes(mime_type, content)

def split_chunks(text: str, size: int = 900) -> List[str]:
    text = re.sub(r"\s+", " ", text).strip()
    return [text[i:i + size] for i in range(0, len(text), size)]

def score_chunk(chunk: str, tokens: List[str]) -> int:
    c = chunk.lower()
    return sum(c.count(t) for t in tokens)

def refresh_cache(creds: service_account.Credentials, project_name: str, folder_id: str) -> None:
    """
    Rebuild the local cache for a given project by downloading all
    files' text in its Drive folder.  Text is stored as separate
    files under ``cache/<project_name>``.  Updates LAST_UPDATE for
    that project.
    """
    service = build_drive_service(creds)
    proj_cache_dir = CACHE_ROOT / project_name
    proj_cache_dir.mkdir(parents=True, exist_ok=True)
    # List all files in folder (use empty query to fetch all)
    try:
        files = service.files().list(
            q=f"'{folder_id}' in parents and trashed=false",
            fields="files(id,name,mimeType,modifiedTime)"
        ).execute().get("files", [])
    except Exception:
        files = []
    for f in files:
        text = download_text(service, f["id"], f.get("mimeType", ""))
        if not text:
            continue
        out_path = proj_cache_dir / f"{f['id']}.txt"
        with open(out_path, "w", encoding="utf-8") as out:
            out.write(text)
    # Update last update timestamp
    from datetime import datetime
    global LAST_UPDATE
    LAST_UPDATE[project_name] = datetime.utcnow().isoformat() + "Z"

def refresh_all_projects(creds: service_account.Credentials) -> None:
    for name, folder_id in _PROJECTS.items():
        refresh_cache(creds, name, folder_id)

def schedule_refresh(creds: service_account.Credentials, interval_hours: int = 6) -> None:
    """Start a daemon thread to refresh all projects every interval."""
    def job():
        while True:
            try:
                refresh_all_projects(creds)
            except Exception:
                pass
            time.sleep(interval_hours * 3600)
    t = threading.Thread(target=job, daemon=True)
    t.start()

def search_and_extract_snippets(
    creds: service_account.Credentials,
    query: str,
    project_name: str,
    max_files: int = 20,
    per_file_snippets: int = 3
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Search the cache for a project and return a list of relevant
    snippets along with citations.  If the cache for the project is
    empty, fall back to a live Drive search.
    """
    tokens = tokenize(query)
    snippets: List[Dict[str, Any]] = []
    citations: List[Dict[str, Any]] = []
    proj_cache_dir = CACHE_ROOT / project_name
    # If cache exists and has files, use it
    if proj_cache_dir.exists():
        for p in list(proj_cache_dir.glob("*.txt"))[:max_files]:
            try:
                text = p.read_text(encoding="utf-8")
            except Exception:
                continue
            chunks = split_chunks(text, 900)
            ranked = sorted(chunks, key=lambda ch: score_chunk(ch, tokens), reverse=True)[:per_file_snippets]
            for r in ranked:
                if score_chunk(r, tokens) == 0:
                    continue
                snippets.append({"source": p.stem, "text": r})
            citations.append({"id": p.stem, "name": p.stem})
        # Return best overall
        snippets = sorted(snippets, key=lambda s: score_chunk(s["text"], tokens), reverse=True)[:12]
        return snippets, citations
    # Fallback to live Drive search for this project if cache missing
    service = build_drive_service(creds)
    folder_id = _PROJECTS.get(project_name)
    if not folder_id:
        return [], []
    files = search_files(service, query, folder_id)[:max_files]
    for f in files:
        text = download_text(service, f["id"], f.get("mimeType", ""))
        if not text:
            continue
        chunks = split_chunks(text, 900)
        ranked = sorted(chunks, key=lambda ch: score_chunk(ch, tokens), reverse=True)[:per_file_snippets]
        for r in ranked:
            if score_chunk(r, tokens) == 0:
                continue
            snippets.append({"source": f['name'], "text": r})
        citations.append({"id": f["id"], "name": f["name"]})
    snippets = sorted(snippets, key=lambda s: score_chunk(s["text"], tokens), reverse=True)[:12]
    return snippets, citations