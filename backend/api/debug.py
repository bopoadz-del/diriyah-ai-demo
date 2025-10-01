"""Utility endpoints that expose Render-friendly debugging information."""

from __future__ import annotations

import os
import platform
import socket
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlparse

from fastapi import APIRouter

router = APIRouter(tags=["debug"])


def _describe_connection_url(url: str | None) -> dict[str, Any]:
    """Summarise the important parts of a connection string without secrets."""

    if not url:
        return {"present": False}

    parsed = urlparse(url)
    database = parsed.path.lstrip("/") or None

    return {
        "present": True,
        "scheme": parsed.scheme,
        "hostname": parsed.hostname,
        "port": parsed.port,
        "database": database,
        "username_present": parsed.username is not None,
    }


def _bool_from_env(name: str, default: bool = False) -> bool:
    """Parse boolean-like values Render commonly stores in env vars."""

    raw = os.getenv(name)
    if raw is None:
        return default

    return raw.lower() in {"1", "true", "yes", "on"}


@router.get("/debug/render", name="render_debug")
def render_debug() -> dict[str, Any]:
    """Return diagnostics that make Render deployments easier to debug."""

    timestamp = datetime.now(tz=timezone.utc).isoformat()

    database_url = os.getenv("DATABASE_URL")
    redis_url = os.getenv("REDIS_URL")

    return {
        "status": "ok",
        "generated_at": timestamp,
        "environment": {
            "render": bool(os.getenv("RENDER")),
            "service": os.getenv("RENDER_SERVICE_ID"),
            "region": os.getenv("RENDER_REGION"),
            "git_commit": os.getenv("RENDER_GIT_COMMIT"),
            "python_version": platform.python_version(),
            "hostname": socket.gethostname(),
        },
        "features": {
            "use_fixture_projects": _bool_from_env("USE_FIXTURE_PROJECTS", True),
            "debug_logging": _bool_from_env("DEBUG", False),
        },
        "services": {
            "database": _describe_connection_url(database_url),
            "redis": _describe_connection_url(redis_url),
            "openai_api_key_present": bool(os.getenv("OPENAI_API_KEY")),
        },
    }

