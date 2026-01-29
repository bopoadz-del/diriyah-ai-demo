"""FastAPI application entry-point with Render-friendly router loading."""

from __future__ import annotations

from importlib import import_module
import logging
import os
import sys
from pathlib import Path
from types import ModuleType
from typing import Iterable, Tuple

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from backend.services.google_drive import (
    drive_credentials_available,
    drive_service_error,
    drive_stubbed,
)


def _configure_logging() -> logging.Logger:
    """Configure structured logging for Render deployments."""

    log_level_name = os.getenv("LOG_LEVEL", "INFO").upper()
    log_level = getattr(logging, log_level_name, logging.INFO)

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

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Note: PDP middleware is not added here to avoid initialization issues
# The PDP system is available via /api/pdp endpoints
# For production, consider implementing PDP middleware with proper dependency injection

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


def _load_module(path: str) -> ModuleType | None:
    """Import ``path`` safely, logging but tolerating missing dependencies."""

    try:
        return import_module(path)
    except Exception as exc:  # pragma: no cover - defensive guard for optional deps
        logger.warning("Skipping router %s due to import error: %s", path, exc)
        return None


def _iter_router_specs() -> Iterable[Tuple[str, str]]:
    """Yield module import paths with their associated API tags."""

    return (
        ("backend.api.advanced_intelligence", "Advanced Intelligence"),
        ("backend.api.intelligence", "Intelligence"),
        ("backend.api.autocad", "AutoCAD"),
        ("backend.api.chat", "Chat"),
        ("backend.api.connectors", "Connectors"),
        ("backend.api.project", "Intel"),
        ("backend.api.cache", "Cache"),
        ("backend.api.alerts", "Alerts"),
        ("backend.api.analytics", "Analytics"),
        ("backend.api.analytics_reports_system", "Analytics Reports"),
        ("backend.api.drive", "Drive"),
        ("backend.api.drive_diagnose", "Drive"),
        ("backend.api.drive_scan", "Drive"),
        ("backend.api.openai_test", "OpenAI"),
        ("backend.api.parsing", "Parsing"),
        ("backend.api.progress_tracking", "Progress Tracking"),
        ("backend.api.upload", "Upload"),
        ("backend.api.qto", "QTO"),
        ("backend.api.vision", "Vision"),
        ("backend.api.speech", "Speech"),
        ("backend.api.projects", "Projects"),
        ("backend.api.preferences", "Preferences"),
        ("backend.api.users", "Users"),
        ("backend.api.workspace", "Workspace"),
        ("backend.api.translation", "Translation"),
        ("backend.api.reasoning", "Reasoning"),
        ("backend.api.pdp", "PDP"),
        ("backend.api.runtime", "Runtime"),
        ("backend.api.hydration", "Hydration"),
        ("backend.api.ops_jobs", "Ops Jobs"),
        ("backend.api.regression", "Regression"),
        ("backend.api.learning", "Learning"),
        ("backend.api.events", "Events"),
        ("backend.api.ops_jobs", "Ops Jobs"),
    )


def _include_router_if_available(module: ModuleType | None, tag: str) -> None:
    """Register the router exposed by ``module`` when present."""

    if module is None:
        return
    router = getattr(module, "router", None)
    if router is not None:
        app.include_router(router, prefix="/api", tags=[tag])


for module_path, tag in _iter_router_specs():
    _include_router_if_available(_load_module(module_path), tag)


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


@app.get("/healthz")
def health_check_alias():
    return health_check()
