"""
main.py
-------

This is the entry point for the Diriyah Brain AI demo.  It spins up a
FastAPI application that serves a simple chat UI and exposes a set
of endpoints for querying project documents, managing caches,
exporting conversations to PDF and interfacing with various stubbed
integrations (WhatsApp, P6, Aconex, Teams, Power BI, etc.).

Important environment variables:

* ``GOOGLE_APPLICATION_CREDENTIALS`` – path to a service account JSON key
* ``OPENAI_API_KEY`` (optional) – when provided, can be used to
  summarise retrieved snippets with an LLM (not wired by default)
"""

from __future__ import annotations

import json
from typing import List, Dict, Any

from fastapi import FastAPI, Request, UploadFile, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from diriyah_brain_ai.drive_adapter import (
    ensure_credentials,
    search_and_extract_snippets,
    refresh_cache,
    schedule_refresh,
    LAST_UPDATE,
)
from diriyah_brain_ai.alerts import generate_alerts
from diriyah_brain_ai.export_pdf import export_chat_to_pdf

from diriyah_brain_ai.quality import router as quality_router
from diriyah_brain_ai.p6 import router as p6_router
from diriyah_brain_ai.aconex import router as aconex_router
from diriyah_brain_ai.teams import router as teams_router
from diriyah_brain_ai.powerbi import router as powerbi_router
from diriyah_brain_ai.whatsapp_adapter import router as whatsapp_router
from diriyah_brain_ai.photos import router as photos_router

import os
from pathlib import Path

# Load projects and users configurations
CONFIG_DIR = Path(__file__).parent
with open(CONFIG_DIR / "projects.json", "r", encoding="utf-8") as f:
    _PROJECTS = json.load(f)["projects"]
with open(CONFIG_DIR / "users.json", "r", encoding="utf-8") as f:
    _USERS = json.load(f)

app = FastAPI(title="Diriyah Brain AI Demo", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory=CONFIG_DIR / "static"), name="static")

# Include stubbed routers
app.include_router(quality_router)
app.include_router(p6_router)
app.include_router(aconex_router)
app.include_router(teams_router)
app.include_router(powerbi_router)
app.include_router(whatsapp_router)
app.include_router(photos_router)

# Global current project variable (used when not specified in query)
CURRENT_PROJECT = None

@app.on_event("startup")
async def on_startup():
    # Start auto refresh thread if credentials are available
    creds = ensure_credentials()
    if creds:
        schedule_refresh(creds, interval_hours=6)

@app.get("/")
def root():
    return FileResponse(CONFIG_DIR / "index.html")

@app.get("/projects/list")
def list_projects():
    """Return the list of available projects."""
    return {"projects": list(_PROJECTS.keys())}

@app.post("/projects/switch")
async def switch_project(payload: Dict[str, Any]):
    """Switch the active project.  Expects JSON { project: name }."""
    global CURRENT_PROJECT
    proj = payload.get("project")
    if proj in _PROJECTS:
        CURRENT_PROJECT = proj
        return {"status": "ok", "project": proj}
    else:
        return JSONResponse({"status": "error", "message": "Unknown project"}, status_code=400)

@app.get("/drive/last-update")
def drive_last_update(project: str | None = None):
    """Return the last refresh timestamp for a project."""
    proj = project or CURRENT_PROJECT
    if not proj:
        return {"timestamp": None}
    return {"timestamp": LAST_UPDATE.get(proj)}

@app.post("/drive/refresh")
def drive_refresh(project: str | None = None):
    """Trigger a manual refresh for the specified project."""
    proj = project or CURRENT_PROJECT
    if not proj or proj not in _PROJECTS:
        return {"message": "Invalid or unspecified project"}
    creds = ensure_credentials()
    if not creds:
        return {"message": "❌ No Drive credentials configured"}
    folder_id = _PROJECTS[proj]
    try:
        refresh_cache(creds, proj, folder_id)
        ts = LAST_UPDATE.get(proj)
        return {"message": f"✅ Refreshed cache for {proj}", "timestamp": ts}
    except Exception as e:
        return {"message": f"⚠️ Error: {e}"}

@app.post("/chat/export/pdf")
async def chat_export_pdf(chat: List[Dict[str, Any]]):
    """Export the provided chat history to a PDF and return it."""
    path = export_chat_to_pdf(chat)
    return FileResponse(path, filename=Path(path).name)

def get_user_projects(user_id: str) -> Dict[str, str]:
    user = _USERS.get(user_id)
    if not user:
        return {}
    if "ALL" in user.get("projects", []):
        return _PROJECTS
    return {p: _PROJECTS[p] for p in user.get("projects", []) if p in _PROJECTS}

def get_user_role(user_id: str) -> str:
    user = _USERS.get(user_id)
    return user.get("role", "engineer") if user else "engineer"

@app.post("/ai/query")
async def ai_query(
    query: str = Form(...),
    role: str = Form("engineer"),
    project: str = Form(None),
    user: str | None = Form(None)
):
    """
    Process a user query.  Searches the specified project (or current
    project if not specified), extracts snippets from the cache, and
    returns a summarised answer with alerts.
    """
    # Determine project
    proj = project or CURRENT_PROJECT
    if not proj:
        return {
            "reply": "Please select a project before asking questions.",
            "alerts": []
        }
    # Determine role from user if provided
    if user:
        role = get_user_role(user)
    # Credentials
    creds = ensure_credentials()
    if not creds:
        return {
            "reply": "❌ No Drive credentials configured.",
            "alerts": []
        }
    # Retrieve snippets
    snippets, citations = search_and_extract_snippets(
        creds, query, proj, max_files=20, per_file_snippets=3
    )
    # Generate reply (simple join; could call OpenAI if key provided)
    if not snippets:
        reply = "No relevant information found."
    else:
        # Create role‑specific prefix
        if role == "director":
            prefix = "📊 Executive summary:\n"
        elif role == "commercial":
            prefix = "💰 Commercial focus:\n"
        else:
            prefix = "🔧 Engineering details:\n"
        joined = "\n".join(f"- {s['text'][:300]}" for s in snippets[:6])
        reply = prefix + joined
    # Alerts
    alerts = generate_alerts(snippets)
    return {
        "reply": reply,
        "alerts": alerts,
        "citations": citations
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)