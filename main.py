import os, io, time, base64, hashlib, secrets
from typing import Optional, List, Dict, Tuple

import requests
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from openai import OpenAI

# ========== Paths ==========
APP_DIR = os.path.dirname(os.path.abspath(__file__))
INDEX_HTML = os.path.join(APP_DIR, "index.html")
DATA_DIR = os.path.join(APP_DIR, "data")
STATIC_DIR = os.path.join(APP_DIR, "static")
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(STATIC_DIR, exist_ok=True)

# ========== App ==========
app = FastAPI(title="Diriyah AI — Full")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_credentials=True,
    allow_methods=["*"], allow_headers=["*"],
)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# ========== Env ==========
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_OAUTH_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_OAUTH_CLIENT_SECRET")
OAUTH_REDIRECT_URI = os.getenv("OAUTH_REDIRECT_URI", "https://diriyah-ai-demo.onrender.com/drive/callback")
OAUTH_SCOPES = "https://www.googleapis.com/auth/drive.readonly"

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_DRIVE_FILES_URL = "https://www.googleapis.com/drive/v3/files"

# ========== OpenAI client ==========
client: Optional[OpenAI] = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None

# ========== Google OAuth state (in-memory for demo) ==========
_OAUTH_STATE: Dict[str, Dict] = {}   # state -> { code_verifier, created }
_USER_TOKEN: Optional[Dict] = None   # { access_token, refresh_token, exp, ... }

def _now() -> int:
    return int(time.time())

def _new_pkce_pair() -> Tuple[str, str]:
    verifier = base64.urlsafe_b64encode(os.urandom(40)).decode().rstrip("=")
    digest = hashlib.sha256(verifier.encode()).digest()
    challenge = base64.urlsafe_b64encode(digest).decode().rstrip("=")
    return verifier, challenge

def _ensure_token() -> str:
    """Return a valid Google access_token; refresh if needed."""
    global _USER_TOKEN
    if not _USER_TOKEN:
        raise HTTPException(401, "Not connected to Google Drive. Use /drive/login.")
    if _USER_TOKEN.get("exp", 0) > _now():
        return _USER_TOKEN["access_token"]
    if not _USER_TOKEN.get("refresh_token"):
        raise HTTPException(401, "Session expired; reconnect Google Drive.")
    data = {
        "client_id": GOOGLE_CLIENT_ID,
        "client_secret": GOOGLE_CLIENT_SECRET,
        "grant_type": "refresh_token",
        "refresh_token": _USER_TOKEN["refresh_token"],
    }
    tok = requests.post(GOOGLE_TOKEN_URL, data=data, timeout=20).json()
    if "access_token" not in tok:
        raise HTTPException(401, f"Refresh failed: {tok}")
    _USER_TOKEN["access_token"] = tok["access_token"]
    _USER_TOKEN["exp"] = _now() + int(tok.get("expires_in", 3600)) - 30
    return _USER_TOKEN["access_token"]

# ========== Root / UI ==========
@app.get("/", response_class=HTMLResponse)
def root():
    if os.path.exists(INDEX_HTML):
        return FileResponse(INDEX_HTML)
    # Fallback minimal UI if index.html is missing
    return HTMLResponse("""
<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Diriyah AI</title></head>
<body style="font-family:system-ui;margin:20px">
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
    const r = await fetch('/ask',{method:'POST',headers:{'content-type':'application/json'},body:JSON.stringify({message:document.getElementById('q').value})});
    const j = await r.json(); setOut(JSON.stringify(j,null,2));
  }
  function setOut(t){document.getElementById('out').textContent=t;}
  </script>
</body></html>
""")

@app.get("/healthz")
def healthz():
    return {"ok": True}

# ========== Vector store (Chroma) ==========
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
            if not d:
                continue
            fname = m.get("name", "file")
            bits.append(f"[{fname}] {d.strip()}")
        return "\n\n".join(bits)
    except Exception:
        return ""

# ========== OpenAI chat ==========
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
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            temperature=0.2,
        )
        return {"answer": resp.choices[0].message.content, "used_context": bool(context)}
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

# ========== Google Drive OAuth ==========
from urllib.parse import urlencode

@app.get("/drive/login")
def drive_login():
    if not (GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET):
        raise HTTPException(500, "Google OAuth not configured (set GOOGLE_OAUTH_CLIENT_ID / GOOGLE_OAUTH_CLIENT_SECRET).")
    state = secrets.token_urlsafe(24)
    verifier, challenge = _new_pkce_pair()
    _OAUTH_STATE[state] = {"code_verifier": verifier, "created": _now()}
    params = {
        "client_id": GOOGLE_CLIENT_ID,
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
        raise HTTPException(400, "Invalid or expired state")
    data = {
        "client_id": GOOGLE_CLIENT_ID,
        "client_secret": GOOGLE_CLIENT_SECRET,
        "code": code,
        "code_verifier": meta["code_verifier"],
        "grant_type": "authorization_code",
        "redirect_uri": OAUTH_REDIRECT_URI,
    }
    tok = requests.post(GOOGLE_TOKEN_URL, data=data, timeout=20).json()
    if "access_token" not in tok:
        raise HTTPException(400, f"Token exchange failed: {tok}")
    tok["exp"] = _now() + int(tok.get("expires_in", 3600)) - 30
    global _USER_TOKEN
    _USER_TOKEN = tok
    return RedirectResponse("/?drive=connected")

@app.get("/drive/list")
def drive_list():
    access_token = _ensure_token()
    headers = {"Authorization": f"Bearer {access_token}"}
    params = {
        "pageSize": 20,
        "fields": "files(id,name,mimeType,modifiedTime,webViewLink,owners(displayName))",
        "orderBy": "modifiedTime desc",
        "q": "trashed=false",
    }
    r = requests.get(GOOGLE_DRIVE_FILES_URL, headers=headers, params=params, timeout=30)
    if r.status_code != 200:
        raise HTTPException(r.status_code, r.text)
    return r.json()

# ========== Drive download / export ==========
EXPORT_MAP = {
    "application/vnd.google-apps.document": "text/plain",
    "application/vnd.google-apps.spreadsheet": "text/csv",
    "application/vnd.google-apps.presentation": "application/pdf",  # export slides to PDF then parse
}

def _drive_export(file_id: str, mime: str, export_mime: str, headers: Dict) -> bytes:
    url = f"https://www.googleapis.com/drive/v3/files/{file_id}/export"
    params = {"mimeType": export_mime}
    resp = requests.get(url, headers=headers, params=params, timeout=60)
    if resp.status_code != 200:
        raise RuntimeError(f"Export failed: {resp.text}")
    return resp.content

def _drive_download(file_id: str, headers: Dict) -> bytes:
    url = f"https://www.googleapis.com/drive/v3/files/{file_id}"
    params = {"alt": "media"}
    resp = requests.get(url, headers=headers, params=params, timeout=120)
    if resp.status_code != 200:
        raise RuntimeError(f"Download failed: {resp.text}")
    return resp.content

# ========== Parsers ==========
def _extract_pdf_text(data: bytes) -> str:
    try:
        import fitz  # PyMuPDF
        out = []
        with fitz.open(stream=data, filetype="pdf") as doc:
            for p in doc:
                out.append(p.get_text())
        return "\n".join(out)
    except Exception as e:
        return f"[PDF parse error] {e}"

def _extract_docx_text(data: bytes) -> str:
    try:
        from docx import Document
        import tempfile
        with tempfile.NamedTemporaryFile(suffix=".docx", delete=True) as tmp:
            tmp.write(data); tmp.flush()
            d = Document(tmp.name)
            return "\n".join(p.text for p in d.paragraphs)
    except Exception as e:
        return f"[DOCX parse error] {e}"

def _extract_xlsx_csv_text(data: bytes, is_xlsx: bool) -> str:
    try:
        import pandas as pd
        import tempfile
        suffix = ".xlsx" if is_xlsx else ".csv"
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=True) as tmp:
            tmp.write(data); tmp.flush()
            if is_xlsx:
                sheets = pd.read_excel(tmp.name, sheet_name=None)
                blocks = []
                for name, df in sheets.items():
                    blocks.append(f"[Sheet: {name}]\n" + df.to_csv(index=False))
                return "\n\n".join(blocks)
            else:
                df = pd.read_csv(tmp.name)
                return df.to_csv(index=False)
    except Exception as e:
        return f"[TABLE parse error] {e}"

def _parse_p6_xer(data: bytes) -> str:
    """
    Built-in lightweight parser for Primavera P6 .xer.
    Scans for %T (table headers) and %R (rows), extracts TASK/ACTIVITY rows.
    """
    try:
        text = data.decode("utf-8", errors="ignore")
    except Exception:
        text = data.decode("latin-1", errors="ignore")

    lines = text.splitlines()
    table = None
    headers: List[str] = []
    out_lines: List[str] = []
    max_rows = 5000

    def flush_table():
        nonlocal table, headers
        table = None
        headers = []

    wanted_tables = {"TASK", "TASKRSRC", "TASKPRED", "ACTIVITY", "ACTVTYPE"}

    def pick(row_dict, keys):
        for k in keys:
            if k in row_dict and row_dict[k]:
                return str(row_dict[k]).strip()
        return ""

    row_count = 0
    for ln in lines:
        if not ln:
            continue
        if ln.startswith("%T"):
            parts = ln.split("\t")
            if len(parts) >= 3:
                table = parts[1].strip().upper()
                headers = parts[2:]
            else:
                flush_table()
            continue
        if ln.startswith("%R") and table and headers:
            parts = ln.split("\t")
            values = parts[1:]
            if len(values) < len(headers):
                values += [""] * (len(headers) - len(values))
            row = dict(zip(headers, values))

            if table in wanted_tables:
                row_count += 1
                act_id = pick(row, ["task_id", "act_id", "task_code"])
                name = pick(row, ["task_name", "act_name"])
                start = pick(row, ["early_start", "act_start_date", "start_date", "start"])
                finish = pick(row, ["early_finish", "act_end_date", "finish_date", "finish"])
                wbs = pick(row, ["wbs_id", "wbs_name"])
                if act_id or name:
                    out_lines.append(f"{act_id} | {name} | {start} → {finish} | {wbs}")

            if row_count >= max_rows:
                out_lines.append("[…truncated rows…]")
                break

    if not out_lines:
        return "[P6 XER parse] No TASK/ACTIVITY rows found"
    return "[P6 XER Activities]\n" + "\n".join(out_lines)

def _parse_p6_xml(data: bytes) -> str:
    try:
        from lxml import etree
        root = etree.fromstring(data)
        ns = root.nsmap.copy() if hasattr(root, "nsmap") else {}
        acts = root.findall(".//Activity", namespaces=ns) or root.findall(".//Activities/Activity", namespaces=ns)
        out = ["[P6 XML Activities]"]
        for a in acts[:5000]:
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

# ========== Convert any Drive file to text ==========
def _file_to_text(meta: Dict, data: bytes) -> str:
    name = meta.get("name", "")
    mime = meta.get("mimeType", "")
    lower = name.lower()

    if mime == "application/pdf":
        return f"[FILE: {name}]\n{_extract_pdf_text(data)}"
    if mime == "application/vnd.openxmlformats-officedocument.wordprocessingml.document" or lower.endswith(".docx"):
        return f"[FILE: {name}]\n{_extract_docx_text(data)}"
    if mime == "text/plain" or lower.endswith(".txt"):
        return f"[FILE: {name}]\n{data.decode('utf-8', errors='ignore')}"
    if mime == "text/csv" or lower.endswith(".csv"):
        return f"[FILE: {name}]\n{_extract_xlsx_csv_text(data, is_xlsx=False)}"
    if mime == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" or lower.endswith(".xlsx"):
        return f"[FILE: {name}]\n{_extract_xlsx_csv_text(data, is_xlsx=True)}"
    if lower.endswith(".xer"):
        return f"[FILE: {name}]\n{_parse_p6_xer(data)}"
    if lower.endswith(".xml"):
        return f"[FILE: {name}]\n{_parse_p6_xml(data)}"

    # Google-native files should be exported before calling this
    return f"[FILE: {name}] [Unsupported type for text extraction]"

# ========== Indexing ==========
_LAST_SYNC_LOG: List[Dict] = []

def _chunk(text: str, chunk_size=1200, overlap=150) -> List[str]:
    out = []
    i, n = 0, len(text)
    while i < n:
        out.append(text[i:i + chunk_size])
        i += max(1, chunk_size - overlap)
    return out

@app.get("/index/run")
def index_run():
    """
    Crawl Drive, export/parse to text, chunk, and store in Chroma.
    """
    access_token = _ensure_token()
    headers = {"Authorization": f"Bearer {access_token}"}
    col = _get_collection()

    added = 0
    seen = 0
    log: List[Dict] = []
    page_token = None
    MAX_FILES = 300  # demo safety cap

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
            seen += 1
            fid = f["id"]; name = f.get("name", ""); mime = f.get("mimeType", "")
            try:
                # Google-native export first
                if mime in EXPORT_MAP:
                    export_mime = EXPORT_MAP[mime]
                    exported = _drive_export(fid, mime, export_mime, headers)
                    if export_mime == "application/pdf":
                        text = _file_to_text(f, exported)
                    elif export_mime == "text/plain":
                        text = f"[FILE: {name}]\n{exported.decode('utf-8', errors='ignore')}"
                    elif export_mime == "text/csv":
                        text = f"[FILE: {name}]\n{_extract_xlsx_csv_text(exported, is_xlsx=False)}"
                    else:
                        text = f"[FILE: {name}] [Unsupported export mime {export_mime}]"
                else:
                    # Binary download
                    data = _drive_download(fid, headers)
                    text = _file_to_text(f, data)

                if not text or not text.strip():
                    log.append({"file": name, "status": "skipped", "reason": "empty text"})
                    continue

                chunks = _chunk(text)
                ids = [f"{fid}::{i}" for i in range(len(chunks))]
                metadatas = [{"file_id": fid, "name": name, "mime": mime} for _ in chunks]
                col.add(ids=ids, documents=chunks, metadatas=metadatas)
                added += len(chunks)
                log.append({"file": name, "status": "indexed", "chunks": len(chunks)})
            except Exception as e:
                log.append({"file": name, "status": "error", "error": str(e)})

            if seen >= MAX_FILES:
                break

        page_token = resp.get("nextPageToken")
        if not page_token or seen >= MAX_FILES:
            break

    global _LAST_SYNC_LOG
    _LAST_SYNC_LOG = log[-200:]  # keep last 200 entries
    return {"files_seen": seen, "chunks_added": added, "log_items": len(log)}

@app.get("/index/status")
def index_status():
    try:
        col = _get_collection()
        return {"chunks": col.count()}
    except Exception as e:
        return {"error": str(e)}

@app.get("/index/log")
def index_log():
    return {"log": _LAST_SYNC_LOG}
