"""YOLO/photo tooling integration helpers."""

from __future__ import annotations

import os
from typing import Any, Dict, Optional

import json
import httpx

from .intent_router import router

_DEFAULT_TIMEOUT = 10.0


class VisionError(RuntimeError):
    """Raised when the vision service encounters a problem."""


class VisionConfigurationError(ValueError):
    """Raised when the vision client is misconfigured."""


def _load_json(response: httpx.Response) -> Dict[str, Any]:
    try:
        return response.json()
    except json.JSONDecodeError:
        return {"raw": response.text}


class VisionClient:
    """Minimal HTTP client for a YOLO/vision microservice."""

    def __init__(
        self,
        *,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        timeout: Optional[float] = None,
    ) -> None:
        configured_url = base_url or os.getenv("VISION_BASE_URL", "").strip()
        configured_key = api_key or os.getenv("VISION_API_KEY", "").strip()
        if not configured_url:
            raise VisionConfigurationError("VISION_BASE_URL is not configured")
        if not configured_key:
            raise VisionConfigurationError("VISION_API_KEY is not configured")

        self._base_url = configured_url.rstrip("/")
        self._api_key = configured_key
        self._timeout = timeout or float(os.getenv("VISION_TIMEOUT", _DEFAULT_TIMEOUT))
        self._health_path = os.getenv("VISION_HEALTH_PATH", "/healthz").lstrip("/")

    def ping(self) -> Dict[str, Any]:
        url = f"{self._base_url}/{self._health_path}" if self._health_path else self._base_url
        headers = {"Authorization": f"Bearer {self._api_key}", "Accept": "application/json"}
        try:
            response = httpx.get(url, headers=headers, timeout=self._timeout)
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise VisionError(f"Vision health check failed: {exc}") from exc
        return _load_json(response)


def check_connection(client: Optional[VisionClient] = None) -> Dict[str, Any]:
    try:
        client = client or VisionClient()
    except VisionConfigurationError as exc:
        return {"service": "vision", "status": "unconfigured", "error": str(exc)}

    try:
        payload = client.ping()
    except VisionError as exc:
        return {"service": "vision", "status": "error", "error": str(exc)}
    return {"service": "vision", "status": "connected", "details": payload}


def handle_vision(message: Any, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    try:
        client = VisionClient()
        health = client.ping()
    except (VisionConfigurationError, VisionError) as exc:
        return {"service": "vision", "status": "error", "error": str(exc)}

    summary = {
        "input": message,
        "context": context or {},
        "health": health,
    }
    return {"service": "vision", "status": "connected", "result": summary}


# Register service on import
router.register("vision", ['\\byolo\\b', '\\bphoto\\b', '\\bimage\\b'], handle_vision)
