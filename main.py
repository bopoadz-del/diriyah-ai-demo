"""
Diriyah AI — FastAPI backend
- OpenAI chat (/ask)
- Google Drive OAuth (/drive/login -> /drive/callback)
- List files (/drive/list)
- Index Drive files into Chroma (/index/run)
- Index status/log (/index/status, /index/log)

Env (Render > Environment):
  OPENAI_API_KEY
  GOOGLE_OAUTH_CLIENT_ID
  GOOGLE_OAUTH_CLIENT_SECRET
  OAUTH_REDIRECT_URI (optional; default: https://diriyah-ai-demo.onrender.com/drive/callback)

Run locally:
  uvicorn main:app --host 0.0.0.0 --port 8000
"""

from __future__ import annotations

import os
import io
import re
import time
import json
import base64
import hashlib
import secrets
import logging
from typing import Dict, List, Optional, Tuple

import requests
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse

from openai import OpenAI

import fitz  # PyMuPDF
from pypdf import PdfReader
from docx import Document
import pandas as pd

import chromadb
from chromadb.config import Settings

# ----------------------------- Logging -----------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)
log = logging.getLogger("diriyah-ai")

# ----------------------------- App & CORS -----------------------------
app = FastAPI(title="Diriyah AI", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten if you know exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ----------------------------- Environment -----------------------------
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

GOOGLE_OAUTH_CLIENT_ID = os.getenv("GOOGLE_OAUTH_CLIENT_ID")
GOOGLE_OAUTH_CLIENT_SECRET = os.getenv("GOOGLE_OAUTH_CLIENT_SECRET")
# You can override this in Render if your URL changes:
OAUTH_REDIRECT_URI = os.getenv(
    "OAUTH_REDIRECT_URI",
    "https://diriyah-ai-demo.onrender.com/drive/callback",
)

OAUTH_SCOPES = "https://www.googleapis.com/auth/drive.readonly"
GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_DRIVE_FILES_URL = "https://www.googleapis.com/drive/v3/files"

if not OPENAI_API_KEY:
    log.warning("OPENAI_API_KEY is not set; /ask will return a helpful error.")

# ----------------------------- OpenAI client -----------------------------
client: Optional[OpenAI] = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None

# ----------------------------- OAuth (demo memory) -----------------------------
_OAUTH_STATE: Dict[str, Dict] = {}  # state -> {code_verifier, created}
_USER_TOKEN: Optional[Dict] = None  # {'access_token','refresh_token','exp',...}

def _now() -> int: return int(time.time())

def _new_pkce_pair() -> Tuple[str, str]:
    verifier = base64.urlsafe_b64encode(os.urandom(40)).decode().rstrip("=")
    digest = hashlib.sha256(verifier.encode()).digest()
    challenge = base64.urlsafe_b64encode(digest).decode().rstrip("=")
    return verifier, challenge

def _ensure_token() -> str:
    """Return a valid Google access token; refresh if needed
