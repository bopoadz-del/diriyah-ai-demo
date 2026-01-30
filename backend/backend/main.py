from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os

from .db import init_db
from .api import projects, chats, messages, drive, upload, speech, vision, ai, admin, settings, analytics

init_flag = os.getenv("INIT_DB_ON_STARTUP", "false").strip().lower()
should_init_db = init_flag not in {"0", "false", "no"}
if should_init_db:
    init_db()

app = FastAPI(title="Diriyah Brain AI")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(projects.router, prefix="/api")
app.include_router(chats.router, prefix="/api")
app.include_router(messages.router, prefix="/api")
app.include_router(drive.router, prefix="/api")
app.include_router(upload.router, prefix="/api")
app.include_router(speech.router, prefix="/api")
app.include_router(vision.router, prefix="/api")
app.include_router(ai.router, prefix="/api")
app.include_router(admin.router, prefix="/api")
app.include_router(settings.router, prefix="/api")
app.include_router(analytics.router, prefix="/api")

@app.get("/health")
def health():
    return {"status": "ok"}
