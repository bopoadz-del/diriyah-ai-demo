import os
import json
from typing import Optional

import uvicorn
from fastapi import FastAPI, UploadFile, Form, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse, Response, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from token_store import set_tokens, get_tokens
from files import process_file
from projects import fetch_projects
from project_folders import (
    list_mappings,
    get_mapping,
    upsert_mapping,
    delete_mapping,
)

# --- OpenAI ---
from openai import OpenAI


def get_openai_client() -> OpenAI:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="OPENAI_API_KEY is not set")
    return OpenAI(api_key=api_key)


# ---------- FastAPI setup ----------
app = FastAPI(title="Diriyah Brain AI", version="1.3.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve static files (the front-end)
app.mount("/static", StaticFiles(directory="."), name="static")


@app.get("/", response_class=FileResponse)
async def root_page():
    if os.path.exists("index.html"):
        return FileResponse("index.html")
    return HTMLResponse("<h1>Diriyah Brain AI</h1><p>No index.html found.</p>", status_code=404)


# ---------- Health & Debug ----------
@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/version")
async def version():
    return {"app": "Diriyah Brain AI", "version": "1.3.0", "python": os.sys.version.split(" ")[0]}


@app.get("/debug/openai")
async def debug_openai():
    try:
        client = get_openai_client()
        import openai as openai_pkg
        return {"openai_pkg_version": getattr(openai_pkg, "__version__", "unknown"), "client_type": type(client).__name__}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ---------- AI Query ----------
@app.post("/ai/query")
async def ai_query(query: str = Form(...)):
    try:
        client = get_openai_client()
        resp = client.chat.completions.create(model="gpt-4o-mini", messages=[{"role": "user", "content": query}])
        return {"reply": resp.choices[0].message.content}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ---------- Google Drive OAuth ----------
from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

CLIENT_SECRETS_FILE = "client_secret.json"
SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]
REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI")


@app.get("/auth/google/start")
async def auth_google():
    if not REDIRECT_URI:
        raise HTTPException(status_code=500, detail="GOOGLE_REDIRECT_URI is not set")
    flow = Flow.from_client_secrets_file(CLIENT_SECRETS_FILE, scopes=SCOPES, redirect_uri=REDIRECT_URI)
    auth_url, _ = flow.authorization_url(prompt="consent")
    return RedirectResponse(auth_url)


@app.get("/auth/google/callback")
async def auth_callback(request: Request):
    if not REDIRECT_URI:
        raise HTTPException(status_code=500, detail="GOOGLE_REDIRECT_URI is not set")
    flow = Flow.from_client_secrets_file(CLIENT_SECRETS_FILE, scopes=SCOPES, redirect_uri=REDIRECT_URI)
    flow.fetch_token(authorization_response=str(request.url))
    creds = flow.credentials
    set_tokens(openai_api_key=os.getenv("OPENAI_API_KEY", ""), google_oauth=creds.to_json())
    return {"status": "Google Drive connected"}


def _get_drive_service():
    creds_json = get_tokens().get("google_oauth") or os.getenv("GOOGLE_OAUTH_JSON")
    if not creds_json:
        return None, {"error": "Not connected to Google Drive"}
    try:
        if isinstance(creds_json, str):
            info = json.loads(creds_json)
        else:
            info = creds_json
        creds = Credentials.from_authorized_user_info(info)
        service = build("drive", "v3", credentials=creds)
        return service, None
    except Exception as e:
        return None, {"error": f"Drive auth error: {e}"}


@app.get("/drive/health")
async def drive_health():
    service, err = _get_drive_service()
    if err:
        return err
    try:
        about = service.about().get(fields="kind").execute()
        return {"status": "ok", "about": about.get("kind")}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Drive health failed: {e}")


@app.get("/drive/files")
async def list_drive_files():
    service, err = _get_drive_service()
    if err:
        return err
    results = service.files().list(pageSize=10, fields="files(id, name, mimeType, modifiedTime)").execute()
    return results.get("files", [])


@app.get("/drive/search")
async def search_drive_files(q: str):
    service, err = _get_drive_service()
    if err:
        return err
    results = service.files().list(
        q=f"name contains '{q}' and trashed=false",
        pageSize=10,
        fields="files(id, name, mimeType, modifiedTime)",
    ).execute()
    return results.get("files", [])


# ---------- Project Folder Mapping CRUD ----------
class FolderMapIn(BaseModel):
    provider: str
    folder_id: str
    display_name: Optional[str] = None


@app.get("/folders")
async def get_project_folders():
    return {"folders": list_mappings()}


@app.get("/folders/{project_name}")
async def get_project_folder(project_name: str):
    m = get_mapping(project_name)
    if not m:
        raise HTTPException(status_code=404, detail="mapping not found")
    return m


@app.post("/folders/{project_name}")
async def upsert_project_folder(project_name: str, body: FolderMapIn):
    upsert_mapping(project_name, body.provider, body.folder_id, body.display_name)
    return {"status": "upserted"}


@app.delete("/folders/{project_name}")
async def delete_project_folder(project_name: str):
    delete_mapping(project_name)
    return {"status": "deleted"}


# ---------- Exports ----------
@app.get("/exports/folders.csv")
async def export_folders_csv():
    import io, csv
    data = list_mappings().values()
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["project_name", "provider", "folder_id", "display_name"])
    for m in data:
        writer.writerow([m.get("project_name",""), m.get("provider",""), m.get("folder_id",""), m.get("display_name","")])
    csv_bytes = buf.getvalue().encode("utf-8")
    headers = {
        "Content-Disposition": 'attachment; filename="folders.csv"'
    }
    return Response(content=csv_bytes, media_type="text/csv", headers=headers)


# ---------- Tokens / Files / Projects ----------
@app.post("/set-tokens")
async def set_tokens_endpoint(openai_api_key: str = Form(...), google_oauth: Optional[str] = Form(None), onedrive_oauth: Optional[str] = Form(None)):
    set_tokens(openai_api_key, google_oauth, onedrive_oauth)
    return {"status": "tokens saved"}


@app.get("/get-tokens")
async def get_tokens_endpoint():
    return get_tokens()


@app.post("/upload-file")
async def upload_file(file: UploadFile):
    content = await file.read()
    result = process_file(file.filename, content)
    return {"status": "processed", "result": result}


@app.get("/projects")
async def get_projects():
    return {"projects": await fetch_projects()}


# ---------- Run ----------
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", 8000)))
