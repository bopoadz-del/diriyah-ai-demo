import os
import logging
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

# ========= Logging =========
logging.basicConfig(level=logging.INFO)
log = logging.getLogger("diriyah-ai")

# ========= Env Vars =========
REQUIRED_ENV = [
    "OPENAI_API_KEY",
    "GOOGLE_CLIENT_ID",
    "GOOGLE_CLIENT_SECRET",
    "OAUTH_REDIRECT_URI",
    "TOKEN_ENCRYPTION_KEY"
]

for var in REQUIRED_ENV:
    if not os.getenv(var):
        raise RuntimeError(f"Missing {var} in environment")

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
OAUTH_REDIRECT_URI = os.getenv("OAUTH_REDIRECT_URI")
USER_ID = os.getenv("DEFAULT_USER_ID", "admin")  # Single user for now

# ========= Clients =========
client = OpenAI(api_key=OPENAI_API_KEY)
log.info("✅ OpenAI client initialized")

chroma_client = chromadb.PersistentClient(path="/app/chroma")
embedding_fn = embedding_functions.OpenAIEmbeddingFunction(
    api_key=OPENAI_API_KEY,
    model_name="text-embedding-3-small"
)
collection = chroma_client.get_or_create_collection(
    "diriyah-ai", 
    embedding_function=embedding_fn,
    metadata={"hnsw:space": "cosine"}
)

# ========= App Setup =========
app = FastAPI(title="Diriyah AI")
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("ALLOWED_ORIGINS", "*").split(","),
    allow_methods=["GET", "POST"],
    allow_headers=["*"]
)
app.mount("/static", StaticFiles(directory="static"), name="static")

# ========= Google OAuth Flow =========
def build_flow() -> Flow:
    return Flow.from_client_secrets_file(
        {
            "web": {
                "client_id": GOOGLE_CLIENT_ID,
                "client_secret": GOOGLE_CLIENT_SECRET,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token"
            }
        },
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
    set_tokens(USER_ID, "google", {
        "token": flow.credentials.token,
        "refresh_token": flow.credentials.refresh_token,
        "expiry": flow.credentials.expiry.isoformat()
    })
    return RedirectResponse("/?auth=success")

def get_drive_service():
    tokens = get_tokens(USER_ID, "google")
    if not tokens:
        raise HTTPException(401, "Not authenticated")
    
    # Build credentials from stored tokens
    # (Simplified for example - use google.oauth2.credentials in real project)
    return build("drive", "v3", credentials=tokens)

# ========= Indexing =========
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

# ========= Q&A =========
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
            model="gpt-4o",
            messages=[
                {
                    "role": "system", 
                    "content": "You are Diriyah AI, a construction assistant."
                },
                {
                    "role": "user", 
                    "content": f"Context: {context}\n\nQuestion: {q}"
                }
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
