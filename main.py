import os, io, time, json, base64, hashlib, secrets
from typing import Optional, List, Dict, Tuple

import requests
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse, HTMLResponse

# ---------- OpenAI ----------
from openai import OpenAI

# ---------- Google ----------
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google.auth.transport.requests import Request as GoogleAuthRequest

# ---------- Paths ----------
APP_DIR = os.path.dirname(os.path.abspath(__file__))
INDEX_HTML = os.path.join(APP_DIR, "index.html")

# ================= FastAPI =================
app = FastAPI(title="Diriyah AI Demo")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"],
)

# ================= Helpers =================
def env(primary: str, fallbacks: List[str] = None, default: Optional[str] = None) -> Optional[str]:
    """Get env var from primary or any fallbacks."""
    fallbacks = fallbacks or []
    val = os.getenv(primary)
    if val: return val
    for k in fallbacks:
        val = os.getenv(k)
        if val: return val
    return default

# ================= OpenAI =================
OPENAI_API_KEY = env("OPENAI_API_KEY", ["OPENAIKEY", "OPENAI"])
client: Optional[OpenAI] = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None

# ================= Google OAuth =================
GOOGLE_CLIENT_ID = env("GOOGLE_OAUTH_CLIENT_ID", ["GOOGLEOAUTHCLIENTID"])
GOOGLE_CLIENT_SECRET = env("GOOGLE_OAUTH_CLIENT_SECRET", ["GOOGLEOAUTHCLIENTSECRET"])
OAUTH_REDIRECT_URI = env(
    "OAUTH_REDIRECT_URI", ["OAUTHREDIRECTURI"],
    default="https://diriyah-ai-demo.onrender.com/drive/callback"
)
OAUTH_SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]

# In-memory creds (OK for demo; resets on redeploy)
_USER_CREDS: Optional[Credentials] = None

def _flow() -> Flow:
    if not (GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET):
        raise HTTPException(500, "Google OAuth not configured on server (env vars missing).")
    return Flow(
        client_config={
            "web": {
                "client_id": GOOGLE_CLIENT_ID,
                "client_secret": GOOGLE_CLIENT_SECRET,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [OAUTH_REDIRECT_URI],
            }
        },
        scopes=OAUTH_SCOPES,
        redirect_uri=OAUTH_REDIRECT_URI,
    )

def _drive():
    """Return Drive service, refreshing tokens if needed."""
    global _USER_CREDS
    if not _USER_CREDS:
        raise HTTPException(401, "Connect Google Drive first (/drive/login).")
    if _USER_CREDS.expired and _USER_CREDS.refresh_token:
        _USER_CREDS.refresh(GoogleAuthRequest())
    return build("drive", "v3", credentials=_USER_CREDS, cache_discovery=False)

# ================= Vector DB (Chroma) =================
# Persist locally (reset on new container); fine for demo.
DATA_DIR = os.path.join(APP_DIR, "data")
os.makedirs(DATA_DIR, exist_ok=True)
_chroma_client = None
_collection = None

def _get_collection():
    global _chroma_client, _collection
    if _collection is not None:
        return _collection
    import chromadb
    _chroma_client = chromadb.PersistentClient(path=os.path.join(DATA_DIR, "chroma"))
    _collection = _chroma_client.get_or_create_collection("drive")
    return _collection

# ================= UI =================
@app.get("/", response_class=HTMLResponse)
def root():
    if os.path.exists(INDEX_HTML):
        return FileResponse(INDEX_HTML)
    return HTMLResponse(f"""
    <html><body style="font-family:system-ui;margin:20px">
      <h2>Diriyah AI</h2>
      <p>OpenAI: {"✅ configured" if client else "⚠️ OPENAI_API_KEY missing"}</p>
      <div style="margin:10px 0">
        <a href="/drive/login" style="padding:8px 12px;background:#1a73e8;color:#fff;border-radius:8px;text-decoration:none">Connect Google Drive</a>
        <a href="/drive/sync" id="syncBtn" style="padding:8px 12px;background:#444;color:#fff;border-radius:8px;text-decoration:none;margin-left:8px">Sync Drive to Index</a>
        <button id="statusBtn" style="padding:8px 12px;background:#0b7;color:#fff;border-radius:8px;text-decoration:none;margin-left:8px">Index Status</button>
        <a href="/drive/list" style="padding:8px 12px;background:#666;color:#fff;border-radius:8px;text-decoration:none;margin-left:8px" target="_blank">List Files (JSON)</a>
      </div>
      <form onsubmit="send(event)">
        <textarea id="q" rows="5" style="width:100%;max-width:700px" placeholder="Ask about anything in your Drive..."></textarea><br>
        <button style="padding:8px 12px;margin-top:8px">Ask</button>
      </form>
      <pre id="out" style="white-space:pre-wrap;margin-top:16px"></pre>
      <script>
        async function send(e){e.preventDefault();
          setOut("Thinking…");
          const r=await fetch('/ask',{method:'POST',headers:{'content-type':'application/json'},
            body:JSON.stringify({message:document.getElementById('q').value})});
          const j=await r.json(); setOut(JSON.stringify(j,null,2));
        }
        function setOut(t){document.getElementById('out').textContent=t;}

        document.getElementById('statusBtn').onclick = async () => {
          setOut("Checking index status…");
          const r = await fetch('/drive/status');
          const j = await r.json();
          setOut("Index status: " + JSON.stringify(j, null, 2));
        };

        const syncBtn = document.getElementById('syncBtn');
        syncBtn.onclick = async (e) => {
          e.preventDefault();
          syncBtn.textContent = "Syncing…";
          try{
            const r = await fetch('/drive/sync');
            const j = await r.json();
            setOut("Sync done: " + JSON.stringify(j, null, 2));
          } finally {
            syncBtn.textContent = "Sync Drive to Index";
          }
        };
      </script>
    </body></html>
    """)

@app.get("/healthz")
def healthz(): return {"ok": True}

# ================= OpenAI Ask (with retrieval) =================
def _retrieve_context(question: str) -> str:
    try:
        col = _get_collection()
        res = col.query(query_texts=[question], n_results=6)
        docs = res.get("documents", [[]])[0]
        mets = res.get("metadatas", [[]])[0]
        snippets = []
        for d, m in zip(docs, mets):
            fname = m.get("name", "file")
            if d and d.strip():
                snippets.append(f"[{fname}] {d.strip()}")
        return "\n\n".join(snippets)
    except Exception:
        return ""

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
        {"role": "system", "content": "You are Diriyah AI. Use the 'Drive context' if present. Answer briefly. Cite file names inline when used."},
        {"role": "user", "content": f"Question:\n{question}\n\nDrive context (may be empty):\n{context}"}
    ]
    try:
        resp = client.chat.completions.create(model="gpt-4o-mini", messages=messages, temperature=0.2)
        return {"answer": resp.choices[0].message.content, "used_context": bool(context)}
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

# ================= Google OAuth Routes =================
@app.get("/drive/login")
def drive_login():
    f = _flow()
    auth_url, state = f.authorization_url(
        access_type="offline", include_granted_scopes="true", prompt="consent"
    )
    app.state.oauth_state = state
    return RedirectResponse(auth_url)

@app.get("/drive/callback")
def drive_callback(request: Request):
    state = request.query_params.get("state")
    if not state or state != getattr(app.state, "oauth_state", None):
        raise HTTPException(400, "Invalid OAuth state")
    f = _flow()
    f.fetch_token(authorization_response=str(request.url))
    creds = f.credentials
    global _USER_CREDS
    _USER_CREDS = creds
    return RedirectResponse("/?drive=connected")

@app.get("/drive/list")
def drive_list():
    svc = _drive()
    files = svc.files().list(
        pageSize=50,
        orderBy="modifiedTime desc",
        fields="files(id,name,mimeType,modifiedTime,webViewLink,owners(displayName))",
        q="trashed=false",
    ).execute()
    return files

# ================= Extraction helpers =================
def _extract_text_from_pdf(bytes_data: bytes) -> str:
    """Extract text from PDF drawings (PyMuPDF)."""
    try:
        import fitz  # PyMuPDF
        text = []
        with fitz.open(stream=bytes_data, filetype="pdf") as doc:
            for page in doc:
                text.append(page.get_text())
        return "\n".join(text)
    except Exception as e:
        return f"[PDF parse error] {e}"

def _parse_p6_xer(bytes_data: bytes) -> str:
    """Parse Primavera P6 .xer into readable lines."""
    try:
        from xer_parser import XERFile
        import io as _io
        xf = XERFile(_io.StringIO(bytes_data.decode("utf-8", errors="ignore")))
        lines = ["[P6 XER Activities]"]
        for a in getattr(xf, "activities", []):
            act_id = getattr(a, "actv_id", "") or getattr(a, "task_id", "") or ""
            name = (getattr(a, "act_name", "") or getattr(a, "task_name", "") or "").strip()
            start = str(getattr(a, "early_start", "") or getattr(a, "start", "") or "")
            finish = str(getattr(a, "early_finish", "") or getattr(a, "finish", "") or "")
            wbs = getattr(a, "wbs_id", "") or getattr(a, "wbs_name", "")
            if act_id or name:
                lines.append(f"{act_id} | {name} | {start} → {finish} | {wbs}")
        # relationships (optional)
        if getattr(xf, "relationships", None):
            lines.append("\n[P6 Logic]")
            for r in xf.relationships[:1000]:
                lines.append(f"{r.pred_id} -{r.rel_type}-> {r.succ_id} (lag {getattr(r,'lag',0)})")
        return "\n".join(lines)
    except Exception as e:
        return f"[P6 XER parse error] {e}"

def _parse_p6_xml(bytes_data: bytes) -> str:
    """Parse Primavera P6 XML export to readable lines."""
    try:
        from lxml import etree
        root = etree.fromstring(bytes_data)
        ns = root.nsmap.copy() if hasattr(root, "nsmap") else {}
        activities = root.findall(".//Activity", namespaces=ns) or root.findall(".//Activities/Activity", namespaces=ns)
        out = ["[P6 XML Activities]"]
        for a in activities:
            def g(tag):
                el = a.find(tag, namespaces=ns)
                return (el.text or "").strip() if el is not None else ""
            act_id = g("ActivityID") or g("Id") or g("TaskID")
            name = g("Name") or g("Title") or ""
            start = g("Start") or g("PlannedStartDate") or g("EarlyStartDate") or ""
            finish = g("Finish") or g("PlannedFinishDate") or g("EarlyFinishDate") or ""
            wbs = g("WBSObjectID") or g("WBSName") or ""
            if act_id or name:
                out.append(f"{act_id} | {name} | {start} → {finish} | {wbs}")
        return "\n".join(out)
    except Exception as e:
        return f"[P6 XML parse error] {e}"

# Google types export mapping
EXPORT_MAP = {
    "application/vnd.google-apps.document": ("text/plain", "txt"),
    "application/vnd.google-apps.spreadsheet": ("text/csv", "csv"),
    "application/vnd.google-apps.presentation": ("text/plain", "txt"),
}

def _download_text(svc, file: Dict) -> str:
    """Download and convert a Drive file to plain text for indexing."""
    fid, mime, name = file["id"], file["mimeType"], file["name"]

    # Google Docs/Sheets/Slides → export
    if mime in EXPORT_MAP:
        export_mime, _ = EXPORT_MAP[mime]
        data = svc.files().export(fileId=fid, mimeType=export_mime).execute()
        content = data.decode("utf-8", errors="ignore")
        return f"[FILE: {name}]\n{content}"

    # PDF → extract text
    if mime == "application/pdf":
        req = svc.files().get_media(fileId=fid)
        from googleapiclient.http import MediaIoBaseDownload
        buf = io.BytesIO(); downloader = MediaIoBaseDownload(buf, req)
        done = False
        while not done:
            _, done = downloader.next_chunk()
        return f"[FILE: {name}]\n{_extract_text_from_pdf(buf.getvalue())}"

    # Plain text
    if mime.startswith("text/"):
        req = svc.files().get_media(fileId=fid)
        from googleapiclient.http import MediaIoBaseDownload
        buf = io.BytesIO(); downloader = MediaIoBaseDownload(buf, req)
        done = False
        while not done:
            _, done = downloader.next_chunk()
        return f"[FILE: {name}]\n{buf.getvalue().decode('utf-8', errors='ignore')}"

    # Primavera P6 by extension
    name_lower = name.lower()
    if name_lower.endswith(".xer") or name_lower.endswith(".xml"):
        req = svc.files().get_media(fileId=fid)
        from googleapiclient.http import MediaIoBaseDownload
        buf = io.BytesIO(); downloader = MediaIoBaseDownload(buf, req)
        done = False
        while not done:
            _, done = downloader.next_chunk()
        data = buf.getvalue()
        parsed = _parse_p6_xer(data) if name_lower.endswith(".xer") else _parse_p6_xml(data)
        return f"[FILE: {name}]\n{parsed}"

    # Unsupported types → skip
    return ""

def _chunk(text: str, chunk_size=1200, overlap=150) -> List[str]:
    out = []
    i, n = 0, len(text)
    while i < n:
        out.append(text[i:i+chunk_size])
        i += max(1, chunk_size - overlap)
    return out

# ================= Sync & Status =================
@app.get("/drive/sync")
def drive_sync():
    """Crawl Drive, extract text, chunk, and store in Chroma index."""
    svc = _drive()
    col = _get_collection()

    added = 0
    seen = 0
    page_token = None
    while True:
        resp = svc.files().list(
            pageSize=200,
            pageToken=page_token,
            orderBy="modifiedTime desc",
            fields="nextPageToken, files(id,name,mimeType,modifiedTime)",
            q="trashed=false",
        ).execute()
        files = resp.get("files", [])
        for f in files:
            seen += 1
            try:
                txt = _download_text(svc, f)
                if not txt or not txt.strip():
                    continue
                chunks = _chunk(txt)
                ids = [f"{f['id']}::{i}" for i in range(len(chunks))]
                metadata = [{"file_id": f["id"], "name": f["name"], "mime": f["mimeType"]} for _ in chunks]
                col.add(ids=ids, documents=chunks, metadatas=metadata)
                added += len(chunks)
            except HttpError:
                continue
            except Exception:
                continue

        page_token = resp.get("nextPageToken")
        if not page_token or seen >= 1000:  # safety cap for demo
            break

    return {"indexed_chunks": added, "files_seen": seen}

@app.get("/drive/status")
def drive_status():
    try:
        col = _get_collection()
        return {"chunks": col.count()}
    except Exception as e:
        return {"error": str(e)}
