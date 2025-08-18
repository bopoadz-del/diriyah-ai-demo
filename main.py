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
    "OAUTH_REDIRECT_URI"
]

for var in REQUIRED_ENV:
    if not os.getenv(var):
        raise RuntimeError(f"Missing {var} in environment")

if len(os.getenv("TOKEN_ENCRYPTION_KEY", "")) < 32:
    raise ValueError("TOKEN_ENCRYPTION_KEY must be at least 32 characters")

# Configuration - UPDATED MODEL
USER_ID = os.getenv("DEFAULT_USER_ID", "admin")
CHROMA_DB_PATH = os.getenv("CHROMA_DB_PATH", "/var/data/chroma")
AI_MODEL = os.getenv("AI_MODEL", "gpt-3.5-turbo")  # Cheaper model
STATIC_DIR = os.getenv("STATIC_DIR", "/var/data/static")
OAUTH_REDIRECT_URI = os.getenv("OAUTH_REDIRECT_URI")
MAX_TOKENS = int(os.getenv("MAX_TOKENS", 150))  # Limit response length

# Create directories if they don't exist
Path(STATIC_DIR).mkdir(parents=True, exist_ok=True)
Path(CHROMA_DB_PATH).mkdir(parents=True, exist_ok=True)

# Initialize clients - WITH COST SAVINGS
client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY"),
    default_headers={"OpenAI-Beta": ""}
)
log.info(f"✅ OpenAI client initialized with {AI_MODEL}")

# Use free local embeddings to save costs
embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
    model_name="all-MiniLM-L6-v2"  # Free alternative
)
chroma_client = chromadb.PersistentClient(path=CHROMA_DB_PATH)
collection = chroma_client.get_or_create_collection(
    name="diriyah-ai",
    embedding_function=embedding_fn,
    metadata={"hnsw:space": "cosine"}
)
log.info("✅ Using free local embeddings for ChromaDB")

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
                "redirect_uris": [OAUTH_REDIRECT_URI]
            }
        },
        scopes=["https://www.googleapis.com/auth/drive.readonly"],
        redirect_uri=OAUTH_REDIRECT_URI
    )

# ... [ALL OTHER ENDPOINTS REMAIN UNCHANGED] ...

# AI endpoints - COST-OPTIMIZED
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
        # Only get context if needed
        if "context" not in q.lower():
            context = ""
        else:
            results = collection.query(
                query_texts=[q],
                n_results=2,  # Fewer results to save tokens
                include=["documents"]
            )
            context = "\n".join(results["documents"][0])[:500] if results["documents"] else ""

        # Optimized prompt
        prompt = f"You are Diriyah AI, a construction assistant. Answer concisely: {q}"
        if context:
            prompt = f"Context: {context}\n\nQuestion: {q}"

        completion = client.chat.completions.create(
            model=AI_MODEL,
            messages=[
                {"role": "system", "content": "You are a professional construction assistant for mega projects in Saudi Arabia. Answer in 1-2 sentences."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=MAX_TOKENS  # Limit token usage
        )
        return {"answer": completion.choices[0].message.content}
    except Exception as e:
        log.exception("Ask error")
        # Fallback to avoid failed responses
        return {"answer": "I'm currently optimizing my response. Please try again with a more specific question about construction projects."}

# Render.com compatibility
if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
