import os, base64, hashlib, secrets, time
from typing import Optional

from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
import requests
from openai import OpenAI

# ---- Paths
APP_DIR = os.path.dirname(os.path.abspath(__file__))
INDEX_PATH = os.path.join(APP_DIR, "index.html")
STATIC_DIR = os.path.join(APP_DIR, "static")
os.makedirs(STATIC_DIR, exist_ok=True)

# ---- App
app = FastAPI(title="Diriyah AI Demo")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_credentials=True,
    allow_methods=["*"], allow_headers=["*"],
)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# ---- OpenAI
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
client: Optional[OpenAI] = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None

# ---- Google OAuth (simple PKCE flow via requests)
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_OAUTH_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_OAUTH_CLIENT_SECRET")
OAUTH_REDIRECT_URI = os.getenv(
    "OAUTH_REDIRECT_URI",
    "https://diriyah-ai-demo.onrender.com/drive/callback"  # <— change if your domain changes
)
OAUTH_SCOPES = "https://www.googleapis.com/auth/drive.readonly"

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_DRIVE_FILES_URL = "https://www.googleapis.com/drive/v3/files"

# In-memory (demo)
_OAUTH_STATE: dict[str, dict] = {}            # state -> {code_verifier, created}
_USER_TOKEN: Optional[dict] = None            # {'access_token','refresh_token','exp'}

def _now() -> int: return int(time.time())

def _new_pkce_pair() -> tuple[str, str]:
    verifier = base64.urlsafe_b64encode(os.urandom(40)).decode().rstrip("=")
    digest = hashlib.sha256(verifier.encode()).digest()
    challenge = base64.urlsafe_b64encode(digest).decode().rstrip("=")
    return verifier, challenge

def _ensure_token() -> str:
    """Return a valid access_token; refresh if needed."""
    global _USER
