import logging
import os
import sys
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from backend.api import (
    advanced_intelligence,
    intelligence,
    alerts,
    analytics,
    analytics_reports_system,
    autocad,
    cache,
    chat,
    connectors,
    drive,
    drive_diagnose,
    drive_scan,
    openai_test,
    parsing,
    progress_tracking,
    preferences,
    project,
    projects,
    qto,
    speech,
    upload,
    users,
    vision,
    workspace,
    translation,
)
from backend.services.google_drive import (
    drive_credentials_available,
    drive_service_error,
    drive_stubbed,
)



def _configure_logging() -> logging.Logger:
    """Configure structured logging for Render deployments."""

    log_level_name = os.getenv("LOG_LEVEL", "INFO").upper()
    log_level = getattr(logging, log_level_name, logging.INFO)

    # ``basicConfig`` is a no-op if the root logger already has handlers, which is
    # the case when running under ``uvicorn`` or ``gunicorn`` locally. Rendering a
    # consistent logging format keeps debugging output predictable in Render.
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
        force=True,
    )

    logger = logging.getLogger(__name__)
    logger.debug("Logging configured", extra={"level": log_level_name})
    return logger


logger = _configure_logging()


app = FastAPI(title="Diriyah Brain AI", version="v1.24")
logger.info("FastAPI application initialised", extra={"version": app.version})
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_BASE_DIR = Path(__file__).resolve().parent
_PROJECT_ROOT = _BASE_DIR.parent
_FRONTEND_DIST_DIR = _PROJECT_ROOT / "frontend_dist"
_FRONTEND_PUBLIC_DIR = _PROJECT_ROOT / "frontend" / "public"

if _FRONTEND_PUBLIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=_FRONTEND_PUBLIC_DIR), name="static")
else:
    logger.warning("frontend public assets directory %s is missing", _FRONTEND_PUBLIC_DIR)

if _FRONTEND_DIST_DIR.exists():
    app.mount(
        "/assets",
        StaticFiles(directory=_FRONTEND_DIST_DIR / "assets", check_dir=False),
        name="assets",
    )
    _INDEX_HTML = _FRONTEND_DIST_DIR / "index.html"
else:
    _INDEX_HTML = _FRONTEND_PUBLIC_DIR / "index.html"

if not _INDEX_HTML.exists():
    logger.warning("frontend index file %s is missing", _INDEX_HTML)
    _INDEX_HTML = None


def _include_router_if_available(module, tag: str) -> None:
    """Register the router exposed by ``module`` when present."""

    router = getattr(module, "router", None)
    if router is not None:
        app.include_router(router, prefix="/api", tags=[tag])


for module, tag in (
    (advanced_intelligence, "Advanced Intelligence"),
    (intelligence, "Intelligence"),
    (autocad, "AutoCAD"),
    (chat, "Chat"),
    (connectors, "Connectors"),
    (project, "Intel"),
    (cache, "Cache"),
    (alerts, "Alerts"),
    (analytics, "Analytics"),
    (analytics_reports_system, "Analytics Reports"),
    (drive, "Drive"),
    (openai_test, "OpenAI"),
    (parsing, "Parsing"),
    (progress_tracking, "Progress Tracking"),
    (upload, "Upload"),
    (qto, "QTO"),
    (vision, "Vision"),
    (speech, "Speech"),
    (projects, "Projects"),
    (preferences, "Preferences"),
    (drive_scan, "Drive"),
    (drive_diagnose, "Drive"),
    (users, "Users"),
    (workspace, "Workspace"),
    (translation, "Translation"),
):
    _include_router_if_available(module, tag)


@app.get("/", include_in_schema=False)
async def serve_frontend() -> FileResponse:
    if _INDEX_HTML is None:
        raise HTTPException(status_code=404, detail="Frontend assets are not available")
    return FileResponse(_INDEX_HTML, media_type="text/html")


@app.get("/health")
def health_check():
    error = drive_service_error()
    return {
        "status": "ok" if error is None else "degraded",
        "version": "v1.24",
        "drive": {
            "credentials_available": drive_credentials_available(),
            "stubbed": drive_stubbed(),
            "error": error,
        },
    }
