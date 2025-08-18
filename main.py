"""
Diriyah AI — FastAPI backend
- /            : serves index.html if present (simple UI)
- /healthz     : health and config flags
- /ask         : RAG + OpenAI chat
- /drive/login : start Google OAuth
- /drive/callback : OAuth redirect
- /drive/list  : list recent Drive files (demo)
- /index/run   : crawl/parse/index Drive files into Chroma
- /index/status: chunk count
- /index/log   : last sync log

Env (Render > Environment):
  OPENAI_API_KEY
  GOOGLE_OAUTH_CLIENT_ID
  GOOGLE_OAUTH_CLIENT_SECRET
  (optional) OAUTH_REDIRECT_URI  e.g. https://diriyah-ai-demo.onrender.com/drive/callback

Tip: if your environment UI blocks underscores, also set:
  OPENAIAPIKEY, GOOGLEOAUTHCLIENTID, GOOGLEOAUTHCLIENTSECRET
"""

from __future__ import annotations

import os, io, re, time, base64, hashlib, secrets, logging
from typing import Dict, List, Optional, Tuple

import requests
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse, FileResponse, HTMLResponse

from urllib.parse import urlencode

# OpenAI 1.x SDK
from openai import OpenAI

# Parsers
import fitz  # PyMuPDF
from pypdf import PdfReader
from docx import Document
import pandas as pd

# Vector DB
import chromadb
from chromadb.config import Settings

# ----------------------------- Logging -----------------------------
logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
log = logging.getLogger("diriyah-ai")

# ----------------------------- App & CORS -----------------------------
app = FastAPI(title="Diriyah AI", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten later
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ----------------------------- Paths -----------------------------
APP_DIR = os.path.dirname(os.path.abspath(__file__))
INDEX_HTML = os.path.join(APP_DIR, "index.html")
CHROMA_DIR = "/tmp/chroma"  # persistent on Render containers during runtime

# ----------------------------- Env (with fallbacks) -----------------------------
def _env(name: str, fallback_names: List[str] = []) -> Optional[str]:
    val = os.getenv(name)
    if val:
        return val
    for alt in fallback_names:
        if os.getenv(alt):
            return os.getenv(alt)
    return None

OPENAI_API_KEY = _env("OPENAI_API_KEY", ["OPENAIAPIKEY"])
GOOGLE_OAUTH_CLIENT_ID = _env("GOOGLE_OAUTH_CLIENT_ID", ["GOOGLEOAUTHCLIENTID"])
GOOGLE_OAUTH_CLIENT_SECRET = _env("GOOGLE_OAUTH_CLIENT_SECRET", ["GOOGLEOAUTHCLIENTSECRET"])

YOUR_URL = os.getenv("YOUR_URL", "https://diriyah-ai-demo.onrender.com")
OAUTH_REDIRECT_URI = os.getenv("OAUTH_REDIRECT_URI", f"{YOUR_URL}/drive/callback")
OAUTH_SCOPES = "https://www.googleapis.com/auth/drive.readonly"

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_DRIVE_FILES_URL = "https://www.googleapis.com/drive/v3/files"

if not OPENAI_API_KEY:
    log.warning("OPENAI_API_KEY is not set; /ask will respond with a helpful message.")

# ----------------------------- OpenAI client -----------------------------
client: Optional[OpenAI] = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None

# ----------------------------- Google OAuth (in-memory demo) -----------------------------
_OAUTH_STATE: Dict[str, Dict] = {}  # state -> {cv: code_verifier, ts: created}
_USER_TOKEN: Optional[Dict] = None  # {'access_token','refresh_token','exp',...}

def _now() -> int:
    return int(time.time())

def _new_pkce_pair() -> Tuple[str, str]:
    verifier = base64.urlsafe_b64encode(os.urandom(40)).decode().rstrip("=")
    digest = hashlib.sha256(verifier.encode()).digest()
    challenge = base64.urlsafe_b64encode(digest).decode().rstrip("=")
    return verifier, challenge

def _ensure_token() -> str:
    """Return a valid Google access token; refresh if needed."""
    global _USER_TOKEN
    if not _USER_TOKEN:
        raise HTTPException(401, "Not connected to Google Drive. Click 'Connect Google Drive' first.")

    if _USER_TOKEN.get("exp", 0) > _now():
        return _USER_TOKEN["access_token"]

    if not _USER_TOKEN.get("refresh_token"):
        raise HTTPException(401, "Session expired; reconnect Google Drive.")

    data = {
        "client_id": GOOGLE_OAUTH_CLIENT_ID,
        "client_secret": GOOGLE_OAUTH_CLIENT_SECRET,
        "grant_type": "refresh_token",
        "refresh_token": _USER_TOKEN["refresh_token"],
    }
    tok = requests.post(GOOGLE_TOKEN_URL, data=data, timeout=20).json()
    if "access_token" not in tok:
        raise HTTPException(401, f"Refresh failed: {tok}")
    _USER_TOKEN["access_token"] = tok["access_token"]
    _USER_TOKEN["exp"] = _now() + int(tok.get("expires_in", 3600)) - 30
    return _USER_TOKEN["access_token"]

# ----------------------------- Root / UI -----------------------------
@app.get("/", response_class=HTMLResponse)
def root():
    if os.path.exists(INDEX_HTML):
        return FileResponse(INDEX_HTML)
    # Fallback tiny page (if index.html missing)
    return HTMLResponse("<h3>Diriyah AI backend is live.</h3><p>Open /drive/login, /index/run, then POST /ask.</p>")

@app.get("/healthz")
def healthz():
    return {
        "ok": True,
        "openai": bool(OPENAI_API_KEY),
        "drive_connected": bool(_USER_TOKEN),
        "redirect_uri": OAUTH_REDIRECT_URI,
    }

# ----------------------------- Chroma (RAG) -----------------------------
_chroma = chromadb.PersistentClient(path=CHROMA_DIR, settings=Settings(allow_reset=True))
_collection = _chroma.get_or_create_collection("drive_docs")

def _embed(texts: List[str]) -> List[List[float]]:
    if not client:
        raise HTTPException(500, "OPENAI_API_KEY not set on server.")
    resp = client.embeddings.create(model="text-embedding-3-small", input=texts)
    return [d.embedding for d in resp.data]

def _retrieve_context(question: str, k: int = 6) -> List[Dict]:
    q_emb = _embed([question])[0]
    res = _collection.query(query_embeddings=[q_emb], n_results=k)
    out: List[Dict] = []
    for i in range(len(res.get("ids", [[]])[0])):
        out.append({
            "id": res["ids"][0][i],
            "text": res["documents"][0][i],
            "meta": res["metadatas"][0][i],
            "distance": res.get("distances", [[None]])[0][i],
        })
    return out

# ----------------------------- Ask (RAG + Chat) -----------------------------
@app.post("/ask")
async def ask(req: Request):
    body = await req.json()
    question = (body or {}).get("question") or (body or {}).get("message")
    if not question:
        return JSONResponse({"error": "Missing 'question' (or 'message')"}, status_code=400)
    if client is None:
        return JSONResponse({"answer": "⚠️ OPENAI_API_KEY not set on the server."}, status_code=200)

    context_bits: List[str] = []
    used = False
    if _collection.count() > 0:
        hits = _retrieve_context(question, k=6)
        for h in hits:
            fname = h["meta"].get("name", "file")
            context_bits.append(f"[{fname}] {h['text'][:1200]}")
        used = len(hits) > 0

    prompt = (
        "You are Diriyah AI. Use Drive context when helpful. "
        "Keep answers concise; cite file names inline like [filename].\n\n"
        f"Question:\n{question}\n\n"
        f"Drive context (may be empty):\n{'\n\n'.join(context_bits) if context_bits else '—'}"
    )

    try:
        res = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
        )
        return {"answer": res.choices[0].message.content, "used_context": used}
    except Exception as e:
        log.exception("OpenAI /ask failed")
        return JSONResponse({"error": str(e)}, status_code=500)

# ----------------------------- Google OAuth -----------------------------
@app.get("/drive/login")
def drive_login():
    if not (GOOGLE_OAUTH_CLIENT_ID and GOOGLE_OAUTH_CLIENT_SECRET):
        raise HTTPException(500, "Google OAuth not configured (set GOOGLE_OAUTH_CLIENT_ID / GOOGLE_OAUTH_CLIENT_SECRET).")
    state = secrets.token_urlsafe(24)
    verifier, challenge = _new_pkce_pair()
    _OAUTH_STATE[state] = {"cv": verifier, "ts": _now()}

    params = {
        "client_id": GOOGLE_OAUTH_CLIENT_ID,
        "redirect_uri": OAUTH_REDIRECT_URI,
        "response_type": "code",
        "scope": OAUTH_SCOPES,
        "access_type": "offline",
        "prompt": "consent",
        "state": state,
        "code_challenge": challenge,
        "code_challenge_method": "S256",
    }
    return RedirectResponse(f"{GOOGLE_AUTH_URL}?{urlencode(params)}")

@app.get("/drive/callback")
def drive_callback(code: str, state: str):
    meta = _OAUTH_STATE.pop(state, None)
    if not meta:
        raise HTTPException(400, "Invalid/expired state")
    data = {
        "client_id": GOOGLE_OAUTH_CLIENT_ID,
        "client_secret": GOOGLE_OAUTH_CLIENT_SECRET,
        "code": code,
        "code_verifier": meta["cv"],
        "grant_type": "authorization_code",
        "redirect_uri": OAUTH_REDIRECT_URI,
    }
    tok = requests.post(GOOGLE_TOKEN_URL, data=data, timeout=20).json()
    if "access_token" not in tok:
        raise HTTPException(400, f"Token exchange failed: {tok}")
    tok["exp"] = _now() + int(tok.get("expires_in", 3600)) - 30
    global _USER_TOKEN
    _USER_TOKEN = tok
    log.info("Google Drive connected")
    return RedirectResponse("/?drive=connected")

@app.get("/drive/list")
def drive_list():
    access = _ensure_token()
    headers = {"Authorization": f"Bearer {access}"}
    params = {
        "pageSize": 50,
        "orderBy": "modifiedTime desc",
        "q": "trashed=false",
        "fields": "files(id,name,mimeType,modifiedTime,webViewLink,owners(displayName),size)",
    }
    r = requests.get(GOOGLE_DRIVE_FILES_URL, headers=headers, params=params, timeout=30)
    if r.status_code != 200:
        raise HTTPException(r.status_code, r.text)
    return r.json()

# ----------------------------- Drive helpers & Parsers -----------------------------
EXPORT_MAP = {
    "application/vnd.google-apps.document": "text/plain",
    "application/vnd.google-apps.spreadsheet": "text/csv",
    "application/vnd.google-apps.presentation": "application/pdf",
}

def _drive_export(file_id: str, export_mime: str, headers: Dict) -> bytes:
    url = f"https://www.googleapis.com/drive/v3/files/{file_id}/export"
    resp = requests.get(url, headers=headers, params={"mimeType": export_mime}, timeout=60)
    if resp.status_code != 200:
        raise RuntimeError(f"Export failed: {resp.text}")
    return resp.content

def _drive_download(file_id: str, headers: Dict) -> bytes:
    url = f"https://www.googleapis.com/drive/v3/files/{file_id}"
    resp = requests.get(url, headers=headers, params={"alt": "media"}, timeout=120)
    if resp.status_code != 200:
        raise RuntimeError(f"Download failed: {resp.text}")
    return resp.content

def _norm_ws(t: str) -> str:
    return re.sub(r"\s+", " ", (t or "")).strip()

def _parse_pdf(data: bytes) -> str:
    try:
        out = []
        with fitz.open(stream=data, filetype="pdf") as doc:
            for p in doc:
                out.append(p.get_text("text"))
        text = "\n".join(out)
        if _norm_ws(text):
            return text
    except Exception:
        pass
    # fallback
    try:
        reader = PdfReader(io.BytesIO(data))
        out = []
        for page in reader.pages:
            out.append(page.extract_text() or "")
        return "\n".join(out)
    except Exception as e:
        return f"[PDF parse error] {e}"

def _parse_docx(data: bytes) -> str:
    try:
        doc = Document(io.BytesIO(data))
        return "\n".join(p.text for p in doc.paragraphs)
    except Exception as e:
        return f"[DOCX parse error] {e}"

def _parse_xlsx_or_csv(data: bytes, is_xlsx: bool) -> str:
    try:
        if is_xlsx:
            xl = pd.ExcelFile(io.BytesIO(data))
            blocks = []
            for sheet in xl.sheet_names:
                df = xl.parse(sheet)
                blocks.append(f"[Sheet: {sheet}]\n{df.to_csv(index=False)}")
            return "\n\n".join(blocks)
        else:
            df = pd.read_csv(io.BytesIO(data))
            return df.to_csv(index=False)
    except Exception as e:
        return f"[TABLE parse error] {e}"

def _file_to_text(meta: Dict, data: bytes) -> str:
    name = meta.get("name", "")
    mime = meta.get("mimeType", "")
    lower = name.lower()

    if mime == "application/pdf" or lower.endswith(".pdf"):
        return f"[FILE: {name}]\n{_parse_pdf(data)}"
    if mime == "application/vnd.openxmlformats-officedocument.wordprocessingml.document" or lower.endswith(".docx"):
        return f"[FILE: {name}]\n{_parse_docx(data)}"
    if mime == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" or lower.endswith(".xlsx"):
        return f"[FILE: {name}]\n{_parse_xlsx_or_csv(data, is_xlsx=True)}"
    if mime == "text/csv" or lower.endswith(".csv"):
        return f"[FILE: {name}]\n{_parse_xlsx_or_csv(data, is_xlsx=False)}"
    if mime == "text/plain" or lower.endswith(".txt"):
        return f"[FILE: {name}]\n{data.decode('utf-8', errors='ignore')}"
    return f"[FILE: {name}] [Unsupported type for text extraction]"

# ----------------------------- Indexing -----------------------------
_LAST_SYNC_LOG: List[Dict] = []

def _chunk(text: str, chunk_size: int = 1200, overlap: int = 150) -> List[str]:
    out: List[str] = []
    i, n = 0, len(text)
    while i < n:
        out.append(text[i:i + chunk_size])
        i += max(1, chunk_size - overlap)
    return out

@app.get("/index/run")
def index_run():
    """
    Crawl Drive (first ~300 files), export/parse to text, chunk, embed, upsert to Chroma.
    """
    access = _ensure_token()
    headers = {"Authorization": f"Bearer {access}"}

    added_chunks = 0
    seen_files = 0
    log_items: List[Dict] = []
    page_token = None
    MAX_FILES = 300

    while True:
        params = {
            "pageSize": 200,
            "pageToken": page_token,
            "orderBy": "modifiedTime desc",
            "q": "trashed=false",
            "fields": "nextPageToken, files(id,name,mimeType,modifiedTime,webViewLink)",
        }
        r = requests.get(GOOGLE_DRIVE_FILES_URL, headers=headers, params=params, timeout=60)
        if r.status_code != 200:
            raise HTTPException(r.status_code, r.text)
        resp = r.json()
        files = resp.get("files", [])

        for f in files:
            seen_files += 1
            fid = f["id"]; name = f.get("name", ""); mime = f.get("mimeType", "")
            try:
                # Google-native export vs binary download
                if mime in EXPORT_MAP:
                    data = _drive_export(fid, EXPORT_MAP[mime], headers)
                else:
                    data = _drive_download(fid, headers)

                text = _file_to_text(f, data)
                if not text or not text.strip():
                    log_items.append({"file": name, "status": "skipped", "reason": "empty"})
                    continue

                chunks = _chunk(text)
                embeds = _embed(chunks)
                ids = [f"{fid}::{i}" for i in range(len(chunks))]
                metas = [{"file_id": fid, "name": name, "mime": mime} for _ in chunks]
                _collection.upsert(ids=ids, documents=chunks, metadatas=metas, embeddings=embeds)

                added_chunks += len(chunks)
                log_items.append({"file": name, "status": "indexed", "chunks": len(chunks)})
            except Exception as e:
                log_items.append({"file": name, "status": "error", "error": str(e)})

            if seen_files >= MAX_FILES:
                break

        page_token = resp.get("nextPageToken")
        if not page_token or seen_files >= MAX_FILES:
            break

    global _LAST_SYNC_LOG
    _LAST_SYNC_LOG = log_items[-200:]
    log.info(f"Index complete: files_seen={seen_files}, chunks_added={added_chunks}")
    return {"files_seen": seen_files, "chunks_added": added_chunks, "log_items": len(log_items)}

@app.get("/index/status")
def index_status():
    try:
        return {"chunks": _collection.count()}
    except Exception as e:
        return {"error": str(e)}

@app.get("/index/log")
def index_log():
    return {"log": _LAST_SYNC_LOG}
