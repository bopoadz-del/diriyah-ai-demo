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

from backend.backend.db import init_db


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


_TRUE_VALUES = {"1", "true", "yes", "y", "on"}
_FALSE_VALUES = {"0", "false", "no", "n", "off"}


def _parse_env_bool(raw_value: str | None, *, default: bool) -> bool:
    if raw_value is None:
        return default
    normalized = raw_value.strip().lower()
    if normalized in _TRUE_VALUES:
        return True
    if normalized in _FALSE_VALUES:
        return False
    return default


def _init_db_if_configured() -> None:
    """Initialise the database if startup init is enabled."""

    raw_flag = os.getenv("INIT_DB_ON_STARTUP")
    should_init = _parse_env_bool(raw_flag, default=True)
    logger.info("INIT_DB_ON_STARTUP=%r parsed=%s", raw_flag, should_init)
    if should_init:
        logger.info("Initialising database on startup")
        init_db()
    else:
        logger.info("Skipping DB init on startup")


_init_db_if_configured()

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
_FRONTEND_DIST_DIR = _BASE_DIR / "frontend_dist"
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
        ("backend.api.ops_jobs", "Ops Jobs"),
        ("backend.api.events", "Events"),
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
    return {
        "status": "ok",
    }


@app.get("/healthz")
def health_check_alias():
    return health_check()
