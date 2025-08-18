import os
import logging
from pathlib import Path
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from openai import OpenAI
import chromadb
from chromadb.utils import embedding_functions

from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
import io

# Import token store
from adapters.token_store import set_tokens, get_tokens

# Disable ChromaDB telemetry to prevent errors
os.environ["ANONYMIZED_TELEMETRY"] = "False"

# Initialize logging
logging.basicConfig(level=logging.INFO)
log = logging.getLogger("diriyah-ai")

# Validate environment variables
REQUIRED_ENV = [
    "OPENAI_API_KEY",
    "GOOGLE_CLIENT_ID",
    "GOOGLE_CLIENT_SECRET",
    "TOKEN_ENCRYPTION_KEY",
    "OAUTH_REDIRECT_URI"  # Required for production
]

for var in REQUIRED_ENV:
    if not os.getenv(var):
        raise RuntimeError(f"Missing {var} in environment")

if len(os.getenv("TOKEN_ENCRYPTION_KEY", "")) < 32:
    raise ValueError("TOKEN_ENCRYPTION_KEY must be at least 32 characters")

# Configuration
USER_ID = os.getenv("DEFAULT_USER_ID", "admin")
CHROMA_DB_PATH = os.getenv("CHROMA_DB_PATH", "/var/data/chroma")
AI_MODEL = os.getenv("AI_MODEL", "gpt-4o")
STATIC_DIR = os.getenv("STATIC_DIR", "/var/data/static")
OAUTH_REDIRECT_URI = os.getenv("OAUTH_REDIRECT_URI")  # From environment

# Create directories if they don't exist
Path(STATIC_DIR).mkdir(parents=True, exist_ok=True)
Path(CHROMA_DB_PATH).mkdir(parents=True, exist_ok=True)

# Initialize clients
client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY"),
    default_headers={"OpenAI-Beta": ""}
)
log.info("✅ OpenAI client initialized")

chroma_client = chromadb.PersistentClient(path=CHROMA_DB_PATH)
embedding_fn = embedding_functions.OpenAIEmbeddingFunction(
    api_key=os.getenv("OPENAI_API_KEY"),
    model_name="text-embedding-3-small"
)
collection = chroma_client.get_or_create_collection(
    name="diriyah-ai",
    embedding_function=embedding_fn,
    metadata={"hnsw:space": "cosine"}
)

# App setup
app = FastAPI(title="Diriyah AI")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"]
)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# Google OAuth flow
def build_flow() -> Flow:
    return Flow.from_client_config(
        client_config={
            "web": {
                "client_id": os.getenv("GOOGLE_CLIENT_ID"),
                "client_secret": os.getenv("GOOGLE_CLIENT_SECRET"),
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [OAUTH_REDIRECT_URI]  # Must match Google Console
            }
        },
        scopes=["https://www.googleapis.com/auth/drive.readonly"],
        redirect_uri=OAUTH_REDIRECT_URI
    )

# UI endpoints
@app.get("/", response_class=HTMLResponse)
def home():
    try:
        return open("./index.html").read()
    except FileNotFoundError:
        return "<h1>Diriyah AI</h1><p>Welcome! Add index.html to enable UI</p>"

@app.get("/healthz")
def healthz():
    return {"status": "ok"}

# Google Drive auth
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
    set_tokens(USER_ID, "google", {
        "token": creds.token,
        "refresh_token": creds.refresh_token,
        "token_uri": creds.token_uri,
        "client_id": os.getenv("GOOGLE_CLIENT_ID"),
        "client_secret": os.getenv("GOOGLE_CLIENT_SECRET"),
        "scopes": creds.scopes,
        "expiry": creds.expiry.isoformat() if creds.expiry else None
    })
    return RedirectResponse("/?auth=success")

def get_drive_service():
    tokens = get_tokens(USER_ID, "google")
    if not tokens:
        raise HTTPException(401, "Not authenticated")
    
    class SimpleCredentials:
        token = tokens["token"]
        refresh_token = tokens["refresh_token"]
        token_uri = tokens["token_uri"]
        client_id = tokens["client_id"]
        client_secret = tokens["client_secret"]
        scopes = tokens["scopes"]
        expiry = tokens["expiry"]
    
    return build("drive", "v3", credentials=SimpleCredentials())

# Indexing endpoints
@app.get("/index/run")
def run_index():
    try:
        service = get_drive_service()
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

            collection.add(
                documents=[text],
                ids=[f["id"]],
                metadatas=[{"name": f["name"], "type": f["mimeType"]}]
            )

        return {"status": "ok", "indexed": len(files)}
    except Exception as e:
        log.exception("Indexing error")
        return JSONResponse(
            status_code=500,
            content={"status": "error", "error": str(e)}
        )

@app.get("/index/status")
def index_status():
    try:
        count = collection.count()
        return {"chunks": count}
    except Exception as e:
        log.error(f"Count error: {str(e)}")
        try:
            ids = collection.get()["ids"]
            return {"chunks": len(ids) if ids else 0}
        except Exception:
            return {"chunks": 0, "error": "Unable to get count"}

# AI endpoints
@app.post("/ask")
async def ask(request: Request):
    data = await request.json()
    q = data.get("question", "").strip()
    if not q:
        return JSONResponse(
            status_code=400,
            content={"error": "Missing question"}
        )

    try:
        results = collection.query(
            query_texts=[q],
            n_results=3,
            include=["documents"]
        )
        context = "\n".join(results["documents"][0]) if results["documents"] else ""

        completion = client.chat.completions.create(
            model=AI_MODEL,
            messages=[
                {"role": "system", "content": "You are Diriyah AI, a construction assistant for mega projects in Saudi Arabia. Answer professionally."},
                {"role": "user", "content": f"Context:\n{context}\n\nQuestion: {q}"}
            ],
            temperature=0.3
        )
        return {"answer": completion.choices[0].message.content}
    except Exception as e:
        log.exception("Ask error")
        return JSONResponse(
            status_code=500,
            content={"error": "Processing failed"}
        )

# Render.com compatibility
if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
