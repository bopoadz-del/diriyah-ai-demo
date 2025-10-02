"""Integration helpers for working with Oracle Aconex."""

from __future__ import annotations

import json
import os
from typing import Any, Dict, Optional

import httpx

from .intent_router import router

_DEFAULT_TIMEOUT = 10.0


class AconexError(RuntimeError):
    """Raised when the Aconex service cannot be reached."""


class AconexConfigurationError(ValueError):
    """Raised when the Aconex client is missing mandatory configuration."""


def _load_json(response: httpx.Response) -> Dict[str, Any]:
    try:
        return response.json()
    except json.JSONDecodeError:
        return {"raw": response.text}


class AconexClient:
    """Small wrapper around the Aconex REST API."""

    def __init__(
        self,
        *,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        timeout: Optional[float] = None,
    ) -> None:
        configured_url = base_url or os.getenv("ACONEX_BASE_URL", "").strip()
        configured_key = api_key or os.getenv("ACONEX_API_KEY", "").strip()
        if not configured_url:
            raise AconexConfigurationError("ACONEX_BASE_URL is not configured")
        if not configured_key:
            raise AconexConfigurationError("ACONEX_API_KEY is not configured")

        self._base_url = configured_url.rstrip("/")
        self._api_key = configured_key
        self._timeout = timeout or float(os.getenv("ACONEX_TIMEOUT", _DEFAULT_TIMEOUT))
        self._health_path = os.getenv("ACONEX_HEALTH_PATH", "/health").lstrip("/")

    def ping(self) -> Dict[str, Any]:
        """Perform a lightweight health-check call against Aconex."""

        url = f"{self._base_url}/{self._health_path}" if self._health_path else self._base_url
        headers = {"Authorization": f"Bearer {self._api_key}", "Accept": "application/json"}
        try:
            response = httpx.get(url, headers=headers, timeout=self._timeout)
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise AconexError(f"Aconex health check failed: {exc}") from exc
        return _load_json(response)


def check_connection(client: Optional[AconexClient] = None) -> Dict[str, Any]:
    """Return a structured payload describing the current connection status."""

    try:
        client = client or AconexClient()
    except AconexConfigurationError as exc:
        return {"service": "aconex", "status": "unconfigured", "error": str(exc)}

    try:
        payload = client.ping()
    except AconexError as exc:
        return {"service": "aconex", "status": "error", "error": str(exc)}
    return {"service": "aconex", "status": "connected", "details": payload}


def handle_aconex(message: Any, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Handle intents destined for the Aconex connector."""

    try:
        client = AconexClient()
        health = client.ping()
    except (AconexConfigurationError, AconexError) as exc:
        return {"service": "aconex", "status": "error", "error": str(exc)}

    summary = {
        "input": message,
        "context": context or {},
        "health": health,
    }
    return {"service": "aconex", "status": "connected", "result": summary}


# Register service on import
router.register("aconex", ["\\baconex\\b"], handle_aconex)
