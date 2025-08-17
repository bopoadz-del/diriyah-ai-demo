import os
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
# --- Debug for API Key ---
print("DEBUG - OPENAI_API_KEY from environment:", os.getenv("OPENAI_API_KEY"))

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise ValueError("❌ OPENAI_API_KEY is missing. Set it in Render > Environment")
    from openai import OpenAI
client = OpenAI(api_key=OPENAI_API_KEY)
# ----- Paths -----
APP_DIR = os.path.dirname(os.path.abspath(__file__))
INDEX_PATH = os.path.join(APP_DIR, "index.html")
STATIC_DIR = os.path.join(APP_DIR, "static")  # optional folder for css/js/images

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
