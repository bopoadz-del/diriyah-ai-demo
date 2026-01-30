import os
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .db import init_db
from .api import projects, chats, messages, drive, upload, speech, vision, ai, admin, settings, analytics

logger = logging.getLogger(__name__)

_TRUE_VALUES = {"1", "true", "yes", "y", "on"}
_FALSE_VALUES = {"0", "false", "no", "n", "off"}


def env_flag(name: str, default: bool) -> tuple[bool, str | None]:
    raw = os.getenv(name)
    if raw is None:
        return default, None
    normalized = raw.strip().lower()
    if normalized in _TRUE_VALUES:
        return True, raw
    if normalized in _FALSE_VALUES:
        return False, raw
    return default, raw


enabled, raw = env_flag("INIT_DB_ON_STARTUP", False)
logger.info("INIT_DB_ON_STARTUP raw=%r parsed=%s", raw, enabled)
if enabled:
    logger.info("Initialising database on startup")
    init_db()
else:
    logger.info("Skipping DB init on startup")

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
