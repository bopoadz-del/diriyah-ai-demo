import os
import json
import uvicorn
from fastapi import FastAPI, UploadFile, Form, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from token_store import set_tokens, get_tokens
from files import process_file
from projects import fetch_projects
from project_folders import list_mappings

from openai import OpenAI
from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

# ---------- FastAPI setup ----------
app = FastAPI(title="Diriyah Brain AI", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="."), name="static")

@app.get("/", response_class=FileResponse)
async def root_page():
    return FileResponse("index.html")

# ---------- OpenAI ----------
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

@app.post("/ai/query")
async def ai_query(query: str = Form(...)):
    """
    Send user query to OpenAI and return assistant reply.
    """
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": query}]
    )
    return {"reply": response.choices[0].message.content}

# ---------- Google Drive OAuth ----------
CLIENT_SECRETS_FILE = "client_secret.json"
SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]
REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI")

@app.get("/auth/google/start")
async def auth_google():
    flow = Flow.from_client_secrets_file(
        CLIENT_SECRETS_FILE, scopes=SCOPES, redirect_uri=REDIRECT_URI
    )
    auth_url, _ = flow.authorization_url(prompt="consent")
    return RedirectResponse(auth_url)

@app.get("/auth/google/callback")
async def auth_callback(request: Request):
    flow = Flow.from_client_secrets_file(
        CLIENT_SECRETS_FILE, scopes=SCOPES, redirect_uri=REDIRECT_URI
    )
    flow.fetch_token(authorization_response=str(request.url))
    creds = flow.credentials
    set_tokens(openai_api_key="", google_oauth=creds.to_json())
    return {"status": "Google Drive connected"}

@app.get("/drive/files")
async def list_drive_files():
    creds_json = get_tokens().get("google_oauth")
    if not creds_json:
        return {"error": "Not connected to Google Drive"}
    creds = Credentials.from_authorized_user_info(json.loads(creds_json))
    service = build("drive", "v3", credentials=creds)
    results = service.files().list(
        pageSize=10, fields="files(id, name, mimeType, modifiedTime)"
    ).execute()
    return results.get("files", [])

@app.get("/drive/search")
async def search_drive_files(q: str):
    creds_json = get_tokens().get("google_oauth")
    if not creds_json:
        return {"error": "Not connected to Google Drive"}
    creds = Credentials.from_authorized_user_info(json.loads(creds_json))
    service = build("drive", "v3", credentials=creds)
    results = service.files().list(
        q=f"name contains '{q}' and trashed=false",
        pageSize=10,
        fields="files(id, name, mimeType, modifiedTime)"
    ).execute()
    return results.get("files", [])

# ---------- Tokens / Files / Projects ----------
@app.post("/set-tokens")
async def set_tokens_endpoint(openai_api_key: str = Form(...),
                              google_oauth: str = Form(None),
                              onedrive_oauth: str = Form(None)):
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

@app.get("/folders")
async def get_project_folders():
    return {"folders": list_mappings()}

# ---------- Run ----------
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
