import os
import logging
from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from openai import OpenAI
import chromadb
from chromadb.utils import embedding_functions

from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
import pickle, io

# ========= Logging =========
logging.basicConfig(level=logging.INFO)
log = logging.getLogger("diriyah-ai")

# ========= Env Vars =========
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
OAUTH_REDIRECT_URI = os.getenv("OAUTH_REDIRECT_URI", "http://localhost:8000/drive/callback")

if not OPENAI_API_KEY:
    raise RuntimeError("Missing OPENAI_API_KEY in environment")

# ========= Clients =========
try:
    client = OpenAI(api_key=OPENAI_API_KEY)
    log.info("✅ OpenAI client initialized")
except Exception as e:
    log.error("❌ Failed to init OpenAI client: %s", e)
    raise

chroma_client = chromadb.PersistentClient(path="/app/chroma")
embedding_fn = embedding_functions.OpenAIEmbeddingFunction(
    api_key=OPENAI_API_KEY,
    model_name="text-embedding-3-small"
)
collection = chroma_client.get_or_create_collection("diriyah-ai", embedding_function=embedding_fn)

# ========= App Setup =========
app = FastAPI(title="Diriyah AI")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_methods=["*"], allow_headers=["*"]
)
app.mount("/static", StaticFiles(directory="static"), name="static")

_index_log = []

# ========= Google OAuth Flow =========
def build_flow() -> Flow:
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
    return Flow.from_client_config(
        client_config,
        scopes=["https://www.googleapis.com/auth/drive.readonly"],
        redirect_uri=OAUTH_REDIRECT_URI
    )

# ========= UI =========
@app.get("/", response_class=HTMLResponse)
def home():
    return open("index.html").read()

@app.get("/healthz")
def healthz():
    return {"status": "ok"}

# ========= Google Drive Auth =========
@app.get("/drive/login")
def drive_login():
    flow = build_flow()
    auth_url, _ = flow.authorization_url(prompt="consent")
    return RedirectResponse(auth_url)

@app.get("/drive/callback")
def drive_callback(request: Request):
    flow = build_flow()
    flow.fetch_token(authorization_response=str(request.url))
    creds = flow.credentials
    with open("token.pkl", "wb") as f:
        pickle.dump(creds, f)
    return RedirectResponse("/")

@app.get("/drive/list")
def drive_list():
    if not os.path.exists("token.pkl"):
        return {"error": "Not authenticated"}
    creds = pickle.load(open("token.pkl", "rb"))
    service = build("drive", "v3", credentials=creds)
    results = service.files().list(pageSize=10).execute()
    return results.get("files", [])

# ========= Indexing =========
@app.get("/index/run")
def run_index():
    try:
        if not os.path.exists("token.pkl"):
            return {"error": "Authenticate first at /drive/login"}
        creds = pickle.load(open("token.pkl", "rb"))
        service = build("drive", "v3", credentials=creds)

        results = service.files().list(pageSize=5).execute()
        files = results.get("files", [])

        for f in files:
            request = service.files().get_media(fileId=f["id"])
            fh = io.BytesIO()
            downloader = MediaIoBaseDownload(fh, request)
            done = False
            while not done:
                _, done = downloader.next_chunk()
            text = fh.getvalue().decode("utf-8", errors="ignore")

            collection.add(documents=[text], ids=[f["id"]])
            _index_log.append(f"Indexed {f['name']}")

        return {"status": "ok", "indexed": len(files)}
    except Exception as e:
        log.exception("Indexing error: %s", e)
        return {"status": "error", "error": str(e)}

@app.get("/index/status")
def index_status():
    try:
        try:
            count = collection.count()
        except AttributeError:
            ids = collection.get()["ids"]
            count = len(ids) if ids else 0
        return {"chunks": count}
    except Exception as e:
        log.exception("Status error: %s", e)
        return {"chunks": 0, "error": str(e)}

@app.get("/index/log")
def index_log():
    return {"log": _index_log[-10:]}

@app.get("/index/summary")
def index_summary():
    try:
        try:
            count = collection.count()
        except AttributeError:
            ids = collection.get()["ids"]
            count = len(ids) if ids else 0
        return {"chunks": count, "recent_logs": _index_log[-10:]}
    except Exception as e:
        log.exception("Summary error: %s", e)
        return {"chunks": 0, "recent_logs": ["Error"], "error": str(e)}

# ========= Q&A =========
@app.post("/ask")
async def ask(data: dict):
    q = data.get("question", "")
    if not q:
        return {"error": "Missing question"}

    try:
        results = collection.query(query_texts=[q], n_results=3)
        context = "\n".join(results["documents"][0]) if results["documents"] else ""

        completion = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are Diriyah AI, a construction assistant."},
                {"role": "user", "content": f"Context: {context}\n\nQ: {q}"}
            ]
        )
        return {"answer": completion.choices[0].message.content}
    except Exception as e:
        log.exception("Ask error: %s", e)
        return {"error": str(e)}
