"""Helper utilities for loading structured data from Google Drive."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from .drive_service import download_file


def _resolve_file_id(candidate: str | None, env_var: str | None) -> str | None:
    """Return the first non-empty identifier from ``candidate`` or ``env_var``."""

    if candidate:
        return candidate
    if env_var:
        env_value = os.getenv(env_var, "").strip()
        if env_value:
            return env_value
    return None


def load_json_resource(
    file_id: str | None = None,
    *,
    env_var: str | None = None,
    default: Any,
) -> Any:
    """Load JSON data from Drive or return ``default`` on failure."""

    resolved = _resolve_file_id(file_id, env_var)
    if not resolved:
        return default

    path = download_file(resolved, extension=".json")
    try:
        with Path(path).open("r", encoding="utf-8") as handle:
            return json.load(handle)
    except Exception:
        return default


def load_text_resource(
    file_id: str | None = None,
    *,
    env_var: str | None = None,
    default: str,
) -> str:
    """Load text content from Drive or return ``default`` on failure."""

    resolved = _resolve_file_id(file_id, env_var)
    if not resolved:
        return default

    path = download_file(resolved, extension=".txt")
    try:
        return Path(path).read_text(encoding="utf-8")
    except Exception:
        return default


__all__ = ["load_json_resource", "load_text_resource"]
