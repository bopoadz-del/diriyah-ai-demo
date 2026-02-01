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
from jwt import PyJWTError
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


_TRUE_VALUES = {"1", "true", "yes", "y", "on"}
_FALSE_VALUES = {"0", "false", "no", "n", "off"}


def env_flag(name: str, default: bool) -> tuple[bool, str | None]:
    """Parse a boolean-ish environment variable with a safe default."""

    raw = os.getenv(name)
    if raw is None:
        return default, None
    normalized = raw.strip().lower()
    if normalized in _TRUE_VALUES:
        return True, raw
    if normalized in _FALSE_VALUES:
        return False, raw
    return default, raw


def _init_db_if_configured() -> None:
    """Initialise the database if startup init is enabled.

    Defaults to True for production/Render deployments to ensure tables exist.
    Set INIT_DB_ON_STARTUP=false to disable (e.g., for tests with fixtures).
    """
    enabled, raw = env_flag("INIT_DB_ON_STARTUP", True)
    logger.info("INIT_DB_ON_STARTUP raw=%r parsed=%s", raw, enabled)
    if enabled:
        logger.info("Initialising database on startup")
        init_db()
    else:
        logger.info("Skipping DB init on startup")


_init_db_if_configured()


def _seed_demo_sources_if_configured() -> None:
    """Seed demo hydration sources if DEMO_SEED_SOURCES is enabled."""
    enabled, raw = env_flag("DEMO_SEED_SOURCES", False)
    logger.info("DEMO_SEED_SOURCES raw=%r parsed=%s", raw, enabled)
    if not enabled:
        return

    try:
        from backend.backend.db import SessionLocal
        from backend.api.hydration import seed_demo_source

        db = SessionLocal()
        try:
            source = seed_demo_source(db)
            if source:
                logger.info(
                    "Demo source seeded: id=%s name=%s workspace=%s",
                    source.id,
                    source.name,
                    source.workspace_id,
                )
        finally:
            db.close()
    except Exception as exc:
        logger.warning("Failed to seed demo sources: %s", exc)


_seed_demo_sources_if_configured()

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


def _iter_frontend_candidates() -> Iterable[Path]:
    env_override = os.getenv("FRONTEND_DIST_DIR")
    if env_override:
        yield Path(env_override)
    yield Path("/app/frontend/dist")
    yield Path("/app/frontend/build")
    yield _PROJECT_ROOT / "frontend" / "dist"
    yield _PROJECT_ROOT / "frontend" / "build"
    yield _BASE_DIR / "frontend_dist"


def _resolve_frontend_dir() -> Path | None:
    for candidate in _iter_frontend_candidates():
        index_file = candidate / "index.html"
        if index_file.exists():
            return candidate
    return None


def _configure_frontend_assets() -> tuple[Path | None, Path | None]:
    frontend_dir = _resolve_frontend_dir()
    if frontend_dir is None:
        logger.warning("Frontend build directory not found; SPA assets are unavailable")
        return None, None
    assets_dir = frontend_dir / "assets"
    if assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=assets_dir, check_dir=False), name="assets")
    index_file = frontend_dir / "index.html"
    return frontend_dir, index_file


_FRONTEND_DIR, _INDEX_HTML = _configure_frontend_assets()


def _is_reserved_path(path: str) -> bool:
    if path == "":
        return False
    if path == "api" or path.startswith("api/"):
        return True
    if path in {"health", "healthz", "openapi.json"}:
        return True
    if path == "docs" or path.startswith("docs/"):
        return True
    if path == "redoc" or path.startswith("redoc/"):
        return True
    return False


@app.get("/", include_in_schema=False)
async def serve_frontend() -> FileResponse:
    if _INDEX_HTML is None:
        raise HTTPException(status_code=404, detail="Frontend assets are not available")
    return FileResponse(_INDEX_HTML, media_type="text/html")


def _decode_token(token: str) -> dict:
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except PyJWTError as exc:
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


@app.get("/{full_path:path}", include_in_schema=False)
async def serve_frontend_spa(full_path: str) -> FileResponse:
    if _INDEX_HTML is None or _FRONTEND_DIR is None:
        raise HTTPException(status_code=404, detail="Frontend assets are not available")
    if _is_reserved_path(full_path):
        raise HTTPException(status_code=404, detail="Not found")
    candidate = _FRONTEND_DIR / full_path
    if full_path and candidate.exists() and candidate.is_file():
        return FileResponse(candidate)
    return FileResponse(_INDEX_HTML, media_type="text/html")
