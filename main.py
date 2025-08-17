import os
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse, JSONResponse
import requests
# --- Debug for API Key ---
print("DEBUG - OPENAI_API_KEY from environment:", os.getenv("OPENAI_API_KEY"))

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise ValueError("❌ OPENAI_API_KEY is missing. Set it in Render > Environment")
    from openai import OpenAI
client = OpenAI(api_key=OPENAI_API_KEY)
# ----- Google OAuth Config -----
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_OAUTH_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_OAUTH_CLIENT_SECRET")
OAUTH_REDIRECT_URI = "https://diriyah-ai-demo.onrender.com/drive/callback"
# ----- Paths -----
APP_DIR = os.path.dirname(os.path.abspath(__file__))
INDEX_PATH = os.path.join(APP_DIR, "index.html")
STATIC_DIR = os.path.join(APP_DIR, "static")  # optional folder for css/js/images
app = FastAPI(title="Diriyah AI Demo")

# --- Google Drive OAuth Routes ---

@app.get("/drive/login")
def drive_login():
    google_auth_url = (
        "https://accounts.google.com/o/oauth2/v2/auth"
        "?response_type=code"
        f"&client_id={GOOGLE_CLIENT_ID}"
        f"&redirect_uri={OAUTH_REDIRECT_URI}"
        "&scope=https://www.googleapis.com/auth/drive.readonly"
        "&access_type=offline"
        "&prompt=consent"
    )
    return RedirectResponse(url=google_auth_url)


@app.get("/drive/callback")
def drive_callback(code: str):
    token_url = "https://oauth2.googleapis.com/token"
    data = {
        "code": code,
        "client_id": GOOGLE_CLIENT_ID,
        "client_secret": GOOGLE_CLIENT_SECRET,
        "redirect_uri": OAUTH_REDIRECT_URI,
        "grant_type": "authorization_code",
    }
    response = requests.post(token_url, data=data)
    tokens = response.json()

    if "access_token" not in tokens:
        return JSONResponse(content={"error": "Failed to get tokens", "details": tokens}, status_code=400)

    return JSONResponse(content={"message": "✅ Google Drive connected!", "tokens": tokens})

app = FastAPI(title="Diriyah AI Demo")

# CORS (safe for quick demo; lock down later if you want)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve /static/* if you later add assets there
if os.path.isdir(STATIC_DIR):
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# ----- Root page -----
@app.get("/")
async def root():
    if os.path.exists(INDEX_PATH):
        return FileResponse(INDEX_PATH)
    return JSONResponse({"detail": "index.html not found in container"}, status_code=500)

# Health
@app.get("/healthz")
async def healthz():
    return {"ok": True}

# ----- AI endpoint -----
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()
client = None
try:
    if OPENAI_API_KEY:
        from openai import OpenAI
        client = OpenAI(api_key=OPENAI_API_KEY)
except Exception:
    client = None

@app.post("/ask")
async def ask(req: Request):
    """Body: { "message": "your question" } -> { "answer": "..." }"""
    try:
        body = await req.json()
        user_msg = (body or {}).get("message", "").strip()
        if not user_msg:
            return JSONResponse({"error": "Empty message"}, status_code=400)

        if client is None:
            return {"answer": "⚠️ OPENAI_API_KEY not set on the server. Add it on Render > Environment."}

        resp = client.chat.completions.create(
            model="gpt-4o-mini",  # or gpt-4o, gpt-4o-mini, etc.
            messages=[
                {"role": "system", "content": "You are Diriyah AI. Answer briefly and helpfully."},
                {"role": "user", "content": user_msg},
            ],
            temperature=0.2,
        )
        answer = resp.choices[0].message.content
        return {"answer": answer}
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)
