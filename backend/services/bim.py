"""Utilities for working with BIM/IFC services."""

from __future__ import annotations

import json
import os
from typing import Any, Dict, Optional

import httpx

from .intent_router import router

_DEFAULT_TIMEOUT = 10.0


class BIMError(RuntimeError):
    """Raised when the BIM service cannot be contacted."""


class BIMConfigurationError(ValueError):
    """Raised when the BIM client is misconfigured."""


def _load_json(response: httpx.Response) -> Dict[str, Any]:
    try:
        return response.json()
    except json.JSONDecodeError:
        return {"raw": response.text}


class BIMClient:
    """Very small helper for invoking a BIM/IFC processing service."""

    def __init__(
        self,
        *,
        base_url: Optional[str] = None,
        token: Optional[str] = None,
        timeout: Optional[float] = None,
    ) -> None:
        configured_url = base_url or os.getenv("BIM_BASE_URL", "").strip()
        configured_token = token or os.getenv("BIM_AUTH_TOKEN", "").strip()
        if not configured_url:
            raise BIMConfigurationError("BIM_BASE_URL is not configured")
        if not configured_token:
            raise BIMConfigurationError("BIM_AUTH_TOKEN is not configured")

        self._base_url = configured_url.rstrip("/")
        self._token = configured_token
        self._timeout = timeout or float(os.getenv("BIM_TIMEOUT", _DEFAULT_TIMEOUT))
        self._health_path = os.getenv("BIM_HEALTH_PATH", "/health").lstrip("/")

    def ping(self) -> Dict[str, Any]:
        url = f"{self._base_url}/{self._health_path}" if self._health_path else self._base_url
        headers = {"Authorization": f"Bearer {self._token}", "Accept": "application/json"}
        try:
            response = httpx.get(url, headers=headers, timeout=self._timeout)
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise BIMError(f"BIM health check failed: {exc}") from exc
        return _load_json(response)


def check_connection(client: Optional[BIMClient] = None) -> Dict[str, Any]:
    try:
        client = client or BIMClient()
    except BIMConfigurationError as exc:
        return {"service": "bim", "status": "unconfigured", "error": str(exc)}

    try:
        payload = client.ping()
    except BIMError as exc:
        return {"service": "bim", "status": "error", "error": str(exc)}
    return {"service": "bim", "status": "connected", "details": payload}


def handle_bim(message: Any, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    try:
        client = BIMClient()
        health = client.ping()
    except (BIMConfigurationError, BIMError) as exc:
        return {"service": "bim", "status": "error", "error": str(exc)}

    summary = {
        "input": message,
        "context": context or {},
        "health": health,
    }
    return {"service": "bim", "status": "connected", "result": summary}


# Register service on import
router.register("bim", ['\\bbim\\b', '\\bifc\\b'], handle_bim)
