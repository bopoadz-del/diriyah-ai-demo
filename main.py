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
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
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
        raise HTTPException(401, f"Refresh failed: {tok}")
    _USER_TOKEN["access_token"] = tok["access_token"]
    _USER_TOKEN["exp"] = _now() + int(tok.get("expires_in", 3600)) - 30
    return _USER_TOKEN["access_token"]

# ====== Simple UI ======
@app.get("/", response_class=HTMLResponse)
def root():
    if os.path.exists(INDEX_HTML):
        return FileResponse(INDEX_HTML)
    # Fallback minimal UI if index.html is missing
    return HTMLResponse("""
    <html><body style="font-family:system-ui;margin:20px">
      <h2>Diriyah AI</h2>
      <div style="margin-bottom:12px">
        <a href="/drive/login" style="padding:8px 12px;background:#1a73e8;color:#fff;border-radius:8px;text-decoration:none">Connect Google Drive</a>
        <a href="/drive/list" style="padding:8px 12px;background:#444;color:#fff;border-radius:8px;text-decoration:none;margin-left:8px" target="_blank">List Files</a>
        <a href="/index/run" style="padding:8px 12px;background:#6b5f52;color:#fff;border-radius:8px;text-decoration:none;margin-left:8px">Index Drive</a>
        <a href="/index/status" style="padding:8px 12px;background:#2d5a33;color:#fff;border-radius:8px;text-decoration:none;margin-left:8px">Index Status</a>
        <a href="/index/log" style="padding:8px 12px;background:#9a3d3d;color:#fff;border-radius:8px;text-decoration:none;margin-left:8px">Sync Log</a>
      </div>
      <form onsubmit="send(event)">
        <textarea id="q" rows="5" style="width:100%;max-width:720px" placeholder="Ask about drawings, reports, schedules..."></textarea><br>
        <button style="padding:8px 12px;margin-top:8px">Ask</button>
      </form>
      <pre id="out" style="white-space:pre-wrap;margin-top:16px"></pre>
      <script>
        async function send(e){e.preventDefault();
          setOut("Thinking…");
          const r=await fetch('/ask',{method:'POST',headers:{'content-type':'application/json'},body:JSON.stringify({message:document.getElementById('q').value})});
          const j=await r.json(); setOut(JSON.stringify(j,null,2));
        }
        function setOut(t){document.getElementById('out').textContent=t;}
      </script>
    </body></html>
    """)

@app.get("/healthz")
def healthz(): return {"ok": True}

# ====== Vector store (Chroma) ======
def _get_collection():
    import chromadb
    path = os.path.join(DATA_DIR, "chroma")
    client = chromadb.PersistentClient(path=path)
    return client.get_or_create_collection("drive")

def _retrieve_context(question: str) -> str:
    try:
        col = _get_collection()
        res = col.query(query_texts=[question], n_results=6)
        docs = res.get("documents", [[]])[0]
        mets = res.get("metadatas", [[]])[0]
        bits = []
        for d, m in zip(docs, mets):
            if not d: continue
            fname = m.get("name", "file")
            bits.append(f"[{fname}] {d.strip()}")
        return "\n\n".join(bits)
    except Exception:
        return ""

# ====== OpenAI Ask with retrieval ======
@app.post("/ask")
async def ask(req: Request):
    body = await req.json()
    question = (body or {}).get("message", "").strip()
    if not question:
        return JSONResponse({"error": "Empty message"}, status_code=400)
    if client is None:
        return {"answer": "⚠️ OPENAI_API_KEY not set on the server."}

    context = _retrieve_context(question)
    messages = [
        {"role": "system", "content": "You are Diriyah AI. Use provided 'Drive context' when relevant. Answer briefly. Cite file names inline."},
        {"role": "user", "content": f"Question:\n{question}\n\nDrive context (may be empty):\n{context}"}
    ]
    try:
        resp = client.chat.completions.create(model="gpt
