import os
import io
import logging
import requests
from typing import Optional, List, Dict

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import FileResponse, RedirectResponse, JSONResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

# --- OpenAI (new SDK) ---
from openai import OpenAI

# --- Google OAuth + Drive API ---
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build, Resource
from google_auth_oauthlib.flow import Flow
from googleapiclient.http import MediaIoBaseDownload

# --- Parsing & Vector DB ---
import fitz  # PyMuPDF
from pypdf import PdfReader
from docx import Document
import pandas as pd
import chromadb

# ========= Logging =========
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("diriyah")

# ========= Constants =========
CHROMA_PATH = "./chroma_data"
DB_COLLECTION_NAME = "drive_documents"
EMBEDDING_MODEL = "text-embedding-3-small"

# ========= Env helpers =========
def getenv_any(*names: str, default: Optional[str] = None) -> Optional[str]:
    for n in names:
        v = os.getenv(n)
        if v:
            return v
    return default

OPENAI_API_KEY = getenv_any("OPENAI_API_KEY", "OPENAIAPIKEY")
GOOGLE_CLIENT_ID = getenv_any("GOOGLE_OAUTH_CLIENT_ID", "GOOGLEOAUTHCLIENTID")
GOOGLE_CLIENT_SECRET = getenv_any("GOOGLE_OAUTH_CLIENT_SECRET", "GOOGLEOAUTHCLIENTSECRET")
OAUTH_REDIRECT_URI = getenv_any("OAUTH_REDIRECT_URI", "REDIRECT_URI")

# Fail fast if redirect not set
if not OAUTH_REDIRECT_URI:
    raise RuntimeError("OAUTH_REDIRECT_URI not set (e.g. https://your-app.onrender.com/drive/callback)")

# ========= OpenAI client =========
client: Optional[OpenAI] = None
if OPENAI_API_KEY:
    try:
        client = OpenAI(api_key=OPENAI_API_KEY)
        log.info("OpenAI client initialized.")
    except Exception as e:
        log.exception("Failed to init OpenAI client: %s", e)
else:
    log.warning("OPENAI_API_KEY not set. RAG features will be disabled.")

# ========= FastAPI app =========
app = FastAPI(title="Diriyah AI Demo", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_credentials=True,
    allow_methods=["*"], allow_headers=["*"],
)

if os.path.exists("index.html"):
    @app.get("/", response_class=HTMLResponse)
    async def root():
        return FileResponse("index.html")
else:
    @app.get("/", response_class=HTMLResponse)
    async def root():
        return HTMLResponse("<h1>Diriyah AI</h1><p>Backend is up.</p>")

if os.path.isdir("static"):
    app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/healthz")
async def healthz():
    return {"ok": True}

# ========= OAuth token store (in-memory) =========
oauth_state: Optional[str] = None
creds: Optional[Credentials] = None

# ========= Google OAuth Flow =========
def build_flow() -> Flow:
    if not (GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET and OAUTH_REDIRECT_URI):
        raise RuntimeError("Google OAuth env not set: GOOGLE_OAUTH_CLIENT_ID / GOOGLE_OAUTH_CLIENT_SECRET / OAUTH_REDIRECT_URI")

    client_config = {
        "web": {
            "client_id": GOOGLE_CLIENT_ID,
            "project_id": "diriyah-ai",
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
            "client_secret": GOOGLE_CLIENT_SECRET,
            "redirect_uris": [OAUTH_REDIRECT_URI],
        }
    }
    scopes = [
        "https://www.googleapis.com/auth/drive.readonly",
        "openid", "email", "profile",
    ]
    return Flow.from_client_config(client_config, scopes=scopes, redirect_uri=OAUTH_REDIRECT_URI)

def get_creds() -> Credentials:
    global creds
    if creds and creds.valid:
        return creds
    if creds and creds.expired and creds.refresh_token:
        try:
            from google.auth.transport import requests as google_requests
            creds.refresh(google_requests.Request())
            log.info("Google OAuth token refreshed successfully.")
            return creds
        except Exception as e:
            log.exception("Failed to refresh Google token: %s", e)
            creds = None
            raise HTTPException(401, "Google token expired. Please reconnect.")
    raise HTTPException(401, "Not connected to Google. Visit /drive/login.")

@app.get("/drive/login")
def drive_login():
    global oauth_state
    flow = build_flow()
    auth_url, state = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent",
    )
    oauth_state = state
    return RedirectResponse(auth_url)

@app.get("/drive/callback")
def drive_callback(request: Request):
    global creds
    flow = build_flow()
    full_url = str(request.url)
    try:
        flow.fetch_token(authorization_response=full_url)
        creds = flow.credentials
        log.info("Google OAuth completed; token acquired.")
        return HTMLResponse("<h3>Google Drive connected ✅</h3><p>You can close this tab.</p>")
    except Exception as e:
        log.exception("OAuth callback error: %s", e)
        raise HTTPException(400, f"OAuth error: {e}")

@app.get("/drive/disconnect")
def drive_disconnect():
    global creds
    creds = None
    return {"ok": True, "message": "Google Drive disconnected"}

# ========= Google Drive helpers =========
def drive_service() -> Resource:
    c = get_creds()
    return build("drive", "v3", credentials=c, cache_discovery=False)

def list_drive_files(page_size: int = 50) -> List[Dict]:
    svc = drive_service()
    files = []
    token = None
    while True:
        resp = svc.files().list(
            pageSize=min(page_size, 100),
            pageToken=token,
            fields="nextPageToken, files(id, name, mimeType, modifiedTime, size)"
        ).execute()
        files.extend(resp.get("files", []))
        token = resp.get("nextPageToken")
        if not token or len(files) >= page_size:
            break
    return files

@app.get("/drive/list")
def drive_list(limit: int = 50):
    try:
        return {"files": list_drive_files(limit)}
    except HTTPException:
        raise
    except Exception as e:
        log.exception("Drive list error: %s", e)
        raise HTTPException(500, "Failed to list Drive files")

# ========= Indexing (Chroma) =========
os.makedirs(CHROMA_PATH, exist_ok=True)
chroma_client = chromadb.PersistentClient(path=CHROMA_PATH)
collection = chroma_client.get_or_create_collection(name=DB_COLLECTION_NAME)

_index_log: List[str] = []
def add_log(msg: str):
    _index_log.append(msg)
    log.info(msg)

def extract_text_from_pdf(stream: io.BytesIO) -> str:
    try:
        stream.seek(0)
        with fitz.open(stream=stream.read(), filetype="pdf") as doc:
            return "\n".join(page.get_text() for page in doc)
    except Exception:
        stream.seek(0)
        reader = PdfReader(stream)
        return "\n".join(p.extract_text() or "" for p in reader.pages)

def extract_text_from_docx(stream: io.BytesIO) -> str:
    stream.seek(0)
    doc = Document(stream)
    return "\n".join(p.text for p in doc.paragraphs)

def extract_text_from_tabular(stream: io.BytesIO, filename: str) -> str:
    stream.seek(0)
    try:
        if filename.lower().endswith(".csv"):
            df = pd.read_csv(stream)
        else:
            df = pd.read_excel(stream)
    except Exception:
        stream.seek(0)
        df = pd.read_excel(stream, engine="openpyxl")
    return df.to_string(index=False)

def download_file_content(file_id: str, mime: str, filename: str) -> Optional[str]:
    svc = drive_service()
    buf = io.BytesIO()
    req = svc.files().get_media(fileId=file_id)
    downloader = MediaIoBaseDownload(buf, req)
    done = False
    while not done:
        _, done = downloader.next_chunk()
    text = ""
    if mime == "application/pdf" or filename.lower().endswith(".pdf"):
        text = extract_text_from_pdf(buf)
    elif mime in (
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/msword",
    ) or filename.lower().endswith(".docx"):
        text = extract_text_from_docx(buf)
    elif any(filename.lower().endswith(ext) for ext in (".xlsx", ".xls", ".csv")):
        text = extract_text_from_tabular(buf, filename)
    elif mime.startswith("text/"):
        buf.seek(0)
        text = buf.read().decode("utf-8", errors="ignore")
    else:
        return None
    return text.strip()

def embed_texts(chunks: List[str]) -> List[List[float]]:
    if not client:
        raise RuntimeError("OpenAI client not initialized")
    resp = client.embeddings.create(model=EMBEDDING_MODEL, input=chunks)
    return [d.embedding for d in resp.data]

@app.get("/index/run")
def index_run(limit: int = 30, chunk_chars: int = 1000):
    _index_log.clear()
    added = 0
    try:
        files = list_drive_files(limit)
        add_log(f"Found {len(files)} candidate files.")
        ids, docs, metas = [], [], []
        for f in files:
            fid, name, mime = f["id"], f["name"], f.get("mimeType", "")
            add_log(f"Downloading: {name} ({mime})")
            try:
                text = download_file_content(fid, mime, name)
                if not text:
                    add_log(f"Skipped (unsupported): {name}")
                    continue
                chunks = [text[i:i+chunk_chars] for i in range(0, len(text), chunk_chars)]
                vecs = embed_texts(chunks)
                for idx, chunk in enumerate(chunks):
                    ids.append(f"{fid}-{idx}")
                    docs.append(chunk)
                    metas.append({"file": name, "file_id": fid, "chunk": idx})
                add_log(f"Prepared {name} -> {len(chunks)} chunks for indexing.")
                added += len(chunks)
            except Exception as e:
                log.exception("Error processing file %s: %s", name, e)
                add_log(f"Error processing {name}: {e}")
        if ids:
            collection.upsert(ids=ids, documents=docs, metadatas=metas)
        add_log(f"Upserted {added} total chunks into ChromaDB.")
        return {"ok": True, "chunks_added": added}
    except HTTPException:
        raise
    except Exception as e:
        log.exception("Index run failed: %s", e)
        raise HTTPException(500, "An internal error occurred during indexing.")

@app.get("/index/status")
def index_status():
    try:
        count = collection.count()
        return {"chunks": count}
    except Exception as e:
        log.exception("Status error: %s", e)
        return {"chunks": 0, "error": "Could not connect to the database."}

@app.get("/index/log")
def index_log():
    return {"log": _index_log[-200:]}

# ========= Ask (RAG) =========
@app.post("/ask")
async def ask(payload: Dict):
    if not client:
        raise HTTPException(503, "OpenAI service is not configured on the server.")
    question = (payload or {}).get("question", "").strip()
    if not question:
        raise HTTPException(400, "Missing 'question'")
    context_bits: List[str] = []
    try:
        results = collection.query(query_texts=[question], n_results=6)
        docs = results.get("documents", [[]])[0]
        metas = results.get("metadatas", [[]])[0]
        for d, m in zip(docs, metas):
            if d:
                fn = m.get("file", "source")
                context_bits.append(f"[{fn}] {d[:800]}")
    except Exception as e:
        log.exception("Chroma query error: %s", e)
    context_block = "\n\n".join(context_bits) if context_bits else "No relevant context found in Drive."
    prompt = (
        "You are Diriyah AI. Use the provided Drive context to answer the user's question. "
        "Keep answers concise and directly address the question. "
        "When you use information from the context, cite the file name inline, like [filename.pdf]."
    )
    try:
        res = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": f"Question: {question}\n\nContext:\n{context_block}"},
            ],
            temperature=0.2,
            max_tokens=500,
        )
        answer = res.choices[0].message.content
    except Exception as e:
        log.exception("OpenAI completion error: %s", e)
        raise HTTPException(500, "Failed to get a response from the AI model.")
    return {"answer": answer}
