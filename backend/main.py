"""FastAPI application entry-point with Render-friendly router loading."""

from __future__ import annotations

from importlib import import_module
import logging
import os
import sys
from pathlib import Path
from types import ModuleType
from typing import Iterable, Tuple

from fastapi import Depends, FastAPI, HTTPException
from fastapi.security import OAuth2PasswordBearer
import jwt
from jwt.exceptions import PyJWTError as JWTError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from backend.backend.db import init_db
from backend.backend.pdp.middleware import PDPMiddleware
from backend.middleware.tenant_enforcer import TenantEnforcerMiddleware


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

JWT_SECRET = os.getenv("JWT_SECRET_KEY", "change-me")
JWT_ALGORITHM = "HS256"
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/token")


def _init_db_if_configured() -> None:
    """Initialise the database if startup init is enabled."""

    init_flag = os.getenv("INIT_DB_ON_STARTUP", "false").strip().lower()
    should_init = init_flag not in {"0", "false", "no"}
    if should_init:
        logger.info("Initialising database on startup")
        init_db()
    else:
        logger.info("Skipping database init on startup", extra={"INIT_DB_ON_STARTUP": init_flag})


_init_db_if_configured()

if os.getenv("ENABLE_BERT_INTENT", "false").lower() == "true":
    logger.info("BERT intent detection enabled")

ENABLE_PDP = os.getenv("ENABLE_PDP_MIDDLEWARE", "true").lower() == "true"
if ENABLE_PDP:
    app.add_middleware(PDPMiddleware)

app.add_middleware(TenantEnforcerMiddleware)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
        ("backend.api.auth", "Auth"),
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


def _decode_token(token: str) -> dict:
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except JWTError as exc:
        raise HTTPException(status_code=401, detail="Invalid token") from exc


@app.get("/protected")
def protected_endpoint(token: str = Depends(oauth2_scheme)) -> dict:
    payload = _decode_token(token)
    return {"status": "ok", "subject": payload.get("sub"), "tenant_id": payload.get("tenant_id")}


@app.get("/health")
def health_check():
    return {
        "status": "ok",
    }


@app.get("/healthz")
def health_check_alias():
    return health_check()
