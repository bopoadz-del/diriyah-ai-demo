"""API surface for reporting connector health."""

from __future__ import annotations

import json
import os
from typing import Any, Dict

import httpx
from fastapi import APIRouter

from backend.services import google_drive
from backend.services.aconex import check_connection as aconex_status
from backend.services.bim import check_connection as bim_status
from backend.services.primavera import check_connection as primavera_status
from backend.services.vision import check_connection as vision_status

router = APIRouter()

_DEFAULT_TIMEOUT = 5.0


def _http_health_from_env(service: str, url_env: str, token_env: str | None = None) -> Dict[str, Any]:
    url = os.getenv(url_env, "").strip()
    if not url:
        return {"service": service, "status": "unconfigured", "error": f"{url_env} is not set"}

    headers = {"Accept": "application/json"}
    if token_env:
        token_value = os.getenv(token_env, "").strip()
        if token_value:
            headers["Authorization"] = f"Bearer {token_value}"

    timeout = float(os.getenv("CONNECTOR_HTTP_TIMEOUT", _DEFAULT_TIMEOUT))
    try:
        response = httpx.get(url, headers=headers, timeout=timeout)
        response.raise_for_status()
    except httpx.HTTPError as exc:
        return {"service": service, "status": "error", "error": f"{service} health check failed: {exc}"}

    try:
        payload = response.json()
    except json.JSONDecodeError:
        payload = {"raw": response.text}
    return {"service": service, "status": "connected", "details": payload}


def _google_drive_status() -> Dict[str, Any]:
    credentials_available = google_drive.drive_credentials_available()
    stubbed = google_drive.drive_stubbed()
    error = google_drive.drive_service_error()
    status = "connected"
    if error:
        status = "error"
    elif stubbed or not credentials_available:
        status = "stubbed"

    payload: Dict[str, Any] = {
        "service": "google_drive",
        "status": status,
        "details": {
            "credentials_available": credentials_available,
            "stubbed": stubbed,
        },
    }
    if error:
        payload["error"] = error
    return payload


def _onedrive_status() -> Dict[str, Any]:
    return _http_health_from_env("onedrive", "ONEDRIVE_HEALTH_URL", "ONEDRIVE_ACCESS_TOKEN")


def _power_bi_status() -> Dict[str, Any]:
    return _http_health_from_env("power_bi", "POWER_BI_HEALTH_URL", "POWER_BI_API_KEY")


def _teams_status() -> Dict[str, Any]:
    health_url = os.getenv("TEAMS_HEALTH_URL", "").strip()
    if health_url:
        return _http_health_from_env("teams", "TEAMS_HEALTH_URL", "TEAMS_API_TOKEN")

    webhook_url = os.getenv("TEAMS_WEBHOOK_URL", "").strip()
    if webhook_url:
        return {
            "service": "teams",
            "status": "configured",
            "details": {"webhook_configured": True},
        }
    return {"service": "teams", "status": "unconfigured", "error": "TEAMS_WEBHOOK_URL is not set"}


def _vision_status() -> Dict[str, Any]:
    payload = vision_status()
    payload = dict(payload)
    payload["service"] = "photo"
    return payload


@router.get("/connectors/list")
def list_connectors() -> Dict[str, Dict[str, Any]]:
    return {
        "google_drive": _google_drive_status(),
        "onedrive": _onedrive_status(),
        "teams": _teams_status(),
        "power_bi": _power_bi_status(),
        "bim": bim_status(),
        "p6": primavera_status(),
        "aconex": aconex_status(),
        "photo": _vision_status(),
    }