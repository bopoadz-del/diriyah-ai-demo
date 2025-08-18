import os, io, time, base64, hashlib, secrets, json
from typing import Optional, List, Dict, Tuple

import requests
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from openai import OpenAI

# ====== Config / Paths ======
APP_DIR = os.path.dirname(os.path.abspath(__file__))
INDEX_HTML = os.path.join(APP_DIR, "index.html")
DATA_DIR = os.path.join(APP_DIR, "data")
os.makedirs(DATA_DIR, exist_ok=True)
STATIC_DIR = os.path.join(APP_DIR, "static")
os.makedirs(STATIC_DIR, exist_ok=True)

# ====== App ======
app = FastAPI(title="Diriyah AI — Full")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"],
)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# ====== Env ======
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")  # required
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_OAUTH_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_OAUTH_CLIENT_SECRET")
OAUTH_REDIRECT_URI = os.getenv("OAUTH_REDIRECT_URI", "https://diriyah-ai-demo.onrender.com/drive/callback")
OAUTH_SCOPES = "https://www.googleapis.com/auth/drive.readonly"

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_DRIVE_FILES_URL = "https://www.googleapis.com/drive/v3/files"

client: Optional[OpenAI] = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None

# ====== Google OAuth demo state (in-memory) ======
_OAUTH_STATE: Dict[str, Dict] = {}     # state -> { code_verifier, created }
_USER_TOKEN: Optional[Dict] = None     # { access_token, refresh_token, exp, ... }

def _now() -> int: return int(time.time())

def _new_pkce_pair() -> Tuple[str, str]:
    verifier = base64.urlsafe_b64encode(os.urandom(40)).decode().rstrip("=")
    digest = hashlib.sha256(verifier.encode()).digest()
    challenge = base64.urlsafe_b64encode(digest).decode().rstrip("=")
    return verifier, challenge

def _ensure_token() -> str:
    """Return a valid Google access_token; refresh if needed."""
    global _USER_TOKEN
    if not _USER_TOKEN:
        raise HTTPException(401, "Not connected to Google Drive. Click 'Connect Google Drive' first.")
    if _USER_TOKEN.get("exp", 0) > _now():
        return _USER_TOKEN["access_token"]
    # Refresh (if we have a refresh token)
    if not _USER_TOKEN.get("refresh_token"):
        raise HTTPException(401, "Session expired; reconnect Google Drive.")
    data = {
        "client_id": GOOGLE_CLIENT_ID, "client_secret": GOOGLE_CLIENT_SECRET,
        "grant_type": "refresh_token", "refresh_token": _USER_TOKEN["refresh_token"],
    }
    tok = requests.post(GOOGLE_TOKEN_URL, data=data, timeout=20).json()
    if "access_token" not in tok:
        raise HTTPException(401, f"Refresh
