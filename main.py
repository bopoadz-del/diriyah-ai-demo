path: main.py

import os import json import uvicorn from fastapi import FastAPI, UploadFile, Form, Request, HTTPException from fastapi.middleware.cors import CORSMiddleware from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse from fastapi.staticfiles import StaticFiles

from token_store import set_tokens, get_tokens from files import process_file from projects import fetch_projects from project_folders import list_mappings

--- OpenAI (lazy init; avoids import-time surprises) ---

from openai import OpenAI

def get_openai_client() -> OpenAI: """Build a clean OpenAI client. Why: Some older builds passed unsupported kwargs like proxies. We ensure only api_key is provided so new SDKs work and old cached wheels don’t inject extras. """ api_key = os.getenv("OPENAI_API_KEY") if not api_key: raise HTTPException(status_code=500, detail="OPENAI_API_KEY is not set") return OpenAI(api_key=api_key)

---------- FastAPI setup ----------

app = FastAPI(title="Diriyah Brain AI", version="1.0.1")

app.add_middleware( CORSMiddleware, allow_origins=[""], allow_credentials=True, allow_methods=[""], allow_headers=["*"], )

Serve static files (the front-end)

app.mount("/static", StaticFiles(directory="."), name="static")

@app.get("/", response_class=FileResponse) async def root_page(): # Serve index.html if present if os.path.exists("index.html"): return FileResponse("index.html") return HTMLResponse("<h1>Diriyah Brain AI</h1><p>No index.html found.</p>", status_code=404)

---------- Health & Debug ----------

@app.get("/health") async def health(): return {"status": "ok"}

@app.get("/debug/openai") async def debug_openai(): try: client = get_openai_client() # Don’t make a network call; just return info so we can verify on Render import openai as openai_pkg  # type: ignore return { "openai_pkg_version": getattr(openai_pkg, "version", "unknown"), "client_type": type(client).name, } except Exception as e: # Surface exact error in deploy logs raise HTTPException(status_code=500, detail=str(e))

---------- AI Query ----------

@app.post("/ai/query") async def ai_query(query: str = Form(...)): """Send user query to OpenAI and return assistant reply.""" try: client = get_openai_client() resp = client.chat.completions.create( model="gpt-4o-mini", messages=[{"role": "user", "content": query}], ) return {"reply": resp.choices[0].message.content} except Exception as e: raise HTTPException(status_code=500, detail=str(e))

---------- Google Drive OAuth ----------

from google_auth_oauthlib.flow import Flow from google.oauth2.credentials import Credentials from googleapiclient.discovery import build

CLIENT_SECRETS_FILE = "client_secret.json" SCOPES = ["https://www.googleapis.com/auth/drive.readonly"] REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI")

@app.get("/auth/google/start") async def auth_google(): flow = Flow.from_client_secrets_file( CLIENT_SECRETS_FILE, scopes=SCOPES, redirect_uri=REDIRECT_URI ) auth_url, _ = flow.authorization_url(prompt="consent") return RedirectResponse(auth_url)

@app.get("/auth/google/callback") async def auth_callback(request: Request): flow = Flow.from_client_secrets_file( CLIENT_SECRETS_FILE, scopes=SCOPES, redirect_uri=REDIRECT_URI ) flow.fetch_token(authorization_response=str(request.url)) creds = flow.credentials # Save the Google OAuth tokens via your existing token_store set_tokens(openai_api_key="", google_oauth=creds.to_json()) return {"status": "Google Drive connected"}

@app.get("/drive/files") async def list_drive_files(): creds_json = get_tokens().get("google_oauth") if not creds_json: return {"error": "Not connected to Google Drive"} creds = Credentials.from_authorized_user_info(json.loads(creds_json)) service = build("drive", "v3", credentials=creds) results = service.files().list( pageSize=10, fields="files(id, name, mimeType, modifiedTime)" ).execute() return results.get("files", [])

@app.get("/drive/search") async def search_drive_files(q: str): creds_json = get_tokens().get("google_oauth") if not creds_json: return {"error": "Not connected to Google Drive"} creds = Credentials.from_authorized_user_info(json.loads(creds_json)) service = build("drive", "v3", credentials=creds) results = service.files().list( q=f"name contains '{q}' and trashed=false", pageSize=10, fields="files(id, name, mimeType, modifiedTime)", ).execute() return results.get("files", [])

---------- Tokens / Files / Projects ----------

@app.post("/set-tokens") async def set_tokens_endpoint( openai_api_key: str = Form(...), google_oauth: str | None = Form(None), onedrive_oauth: str | None = Form(None), ): set_tokens(openai_api_key, google_oauth, onedrive_oauth) return {"status": "tokens saved"}

@app.get("/get-tokens") async def get_tokens_endpoint(): return get_tokens()

@app.post("/upload-file") async def upload_file(file: UploadFile): content = await file.read() result = process_file(file.filename, content) return {"status": "processed", "result": result}

@app.get("/projects") async def get_projects(): return {"projects": await fetch_projects()}

@app.get("/folders") async def get_project_folders(): return {"folders": list_mappings()}

---------- Run ----------

if name == "main": uvicorn.run(app, host="0.0.0.0", port=8000)

