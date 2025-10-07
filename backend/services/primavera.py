"""Primavera P6 service integration helpers."""

from __future__ import annotations

import json
import os
from typing import Any, Dict, Optional

import httpx

from .intent_router import router
from .drive_payloads import load_json_resource

_DEFAULT_TIMEOUT = 10.0


class PrimaveraError(RuntimeError):
    """Raised when Primavera cannot be contacted."""


class PrimaveraConfigurationError(ValueError):
    """Raised when the Primavera client is missing configuration."""


def _load_json(response: httpx.Response) -> Dict[str, Any]:
    try:
        return response.json()
    except json.JSONDecodeError:
        return {"raw": response.text}


class PrimaveraClient:
    """Very small HTTP client for Primavera P6 endpoints."""

    def __init__(
        self,
        *,
        base_url: Optional[str] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
        timeout: Optional[float] = None,
    ) -> None:
        configured_url = base_url or os.getenv("PRIMAVERA_BASE_URL", "").strip()
        configured_user = username or os.getenv("PRIMAVERA_USERNAME", "").strip()
        configured_password = password or os.getenv("PRIMAVERA_PASSWORD", "").strip()
        if not configured_url:
            raise PrimaveraConfigurationError("PRIMAVERA_BASE_URL is not configured")
        if not configured_user or not configured_password:
            raise PrimaveraConfigurationError("PRIMAVERA_USERNAME/PRIMAVERA_PASSWORD must be configured")

        self._base_url = configured_url.rstrip("/")
        self._auth = (configured_user, configured_password)
        self._timeout = timeout or float(os.getenv("PRIMAVERA_TIMEOUT", _DEFAULT_TIMEOUT))
        self._health_path = os.getenv("PRIMAVERA_HEALTH_PATH", "/health").lstrip("/")

    def ping(self) -> Dict[str, Any]:
        url = f"{self._base_url}/{self._health_path}" if self._health_path else self._base_url
        try:
            response = httpx.get(url, auth=self._auth, timeout=self._timeout)
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise PrimaveraError(f"Primavera health check failed: {exc}") from exc
        return _load_json(response)


def check_connection(client: Optional[PrimaveraClient] = None) -> Dict[str, Any]:
    try:
        client = client or PrimaveraClient()
    except PrimaveraConfigurationError as exc:
        return {
            "service": "p6",
            "status": "stubbed",
            "details": _drive_backed_schedule(),
            "error": str(exc),
        }

    try:
        payload = client.ping()
    except PrimaveraError as exc:
        return {
            "service": "p6",
            "status": "stubbed",
            "details": _drive_backed_schedule(),
            "error": str(exc),
        }
    return {"service": "p6", "status": "connected", "details": payload}


def handle_primavera(message: Any, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    try:
        client = PrimaveraClient()
        health = client.ping()
        status = "connected"
        schedule = health
    except (PrimaveraConfigurationError, PrimaveraError) as exc:
        status = "stubbed"
        schedule = _drive_backed_schedule()
        schedule["error"] = str(exc)

    summary = {
        "input": message,
        "context": context or {},
        "schedule": schedule,
    }
    return {"service": "primavera", "status": status, "result": summary}


# Register service on import
router.register("primavera", ['\\bprimavera\\b', '\\.xer\\b'], handle_primavera)
_STUB_SCHEDULE = {
    "activities": [
        {
            "id": "ACT-100",
            "name": "Mobilisation",
            "planned_start": "2024-04-01",
            "planned_finish": "2024-04-05",
            "status": "complete",
        },
        {
            "id": "ACT-140",
            "name": "Podium slab pour",
            "planned_start": "2024-04-08",
            "planned_finish": "2024-04-15",
            "status": "in-progress",
            "percent_complete": 65,
        },
        {
            "id": "ACT-200",
            "name": "Façade bracket installation",
            "planned_start": "2024-04-16",
            "planned_finish": "2024-04-25",
            "status": "not-started",
        },
    ],
    "milestones": [
        {"id": "MS-01", "name": "Podium complete", "status": "at-risk"},
        {"id": "MS-02", "name": "Tower topping", "status": "on-track"},
    ],
}


def _drive_backed_schedule(file_id: str | None = None) -> Dict[str, Any]:
    payload = load_json_resource(file_id, env_var="PRIMAVERA_DRIVE_FILE_ID", default=_STUB_SCHEDULE)
    if isinstance(payload, dict):
        return payload
    return dict(_STUB_SCHEDULE)
