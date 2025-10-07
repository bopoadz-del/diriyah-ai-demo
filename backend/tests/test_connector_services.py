"""Tests covering connector service integrations and API status reporting."""

from __future__ import annotations

import json
from typing import Any, Dict

import httpx
import pytest

from backend.api import connectors
from backend.services import aconex, bim, primavera, vision


def _response(url: str, *, status_code: int = 200, json_body: Dict[str, Any] | None = None) -> httpx.Response:
    request = httpx.Request("GET", url)
    if json_body is None:
        content = b"{}"
    else:
        content = json.dumps(json_body).encode()
    return httpx.Response(status_code=status_code, request=request, content=content)


def test_aconex_check_connection_success(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ACONEX_BASE_URL", "https://aconex.test")
    monkeypatch.setenv("ACONEX_API_KEY", "secret")

    def fake_get(url: str, *, headers: Dict[str, str], timeout: float) -> httpx.Response:
        assert url == "https://aconex.test/health"
        assert headers["Authorization"].startswith("Bearer ")
        return _response(url, json_body={"status": "ok"})

    monkeypatch.setattr(aconex.httpx, "get", fake_get)
    status = aconex.check_connection()
    assert status["status"] == "connected"
    assert status["details"]["status"] == "ok"


def test_aconex_check_connection_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ACONEX_BASE_URL", "https://aconex.test")
    monkeypatch.setenv("ACONEX_API_KEY", "secret")

    def fake_get(url: str, *, headers: Dict[str, str], timeout: float) -> httpx.Response:
        raise httpx.ConnectError("boom", request=httpx.Request("GET", url))

    monkeypatch.setattr(aconex.httpx, "get", fake_get)
    status = aconex.check_connection()
    assert status["status"] == "stubbed"
    assert "boom" in status["error"]
    assert "transmittals" in status["details"]


def test_primavera_check_connection_success(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PRIMAVERA_BASE_URL", "https://p6.test")
    monkeypatch.setenv("PRIMAVERA_USERNAME", "user")
    monkeypatch.setenv("PRIMAVERA_PASSWORD", "pass")

    def fake_get(url: str, *, auth: Any, timeout: float) -> httpx.Response:
        assert url == "https://p6.test/health"
        assert auth == ("user", "pass")
        return _response(url, json_body={"status": "ok"})

    monkeypatch.setattr(primavera.httpx, "get", fake_get)
    status = primavera.check_connection()
    assert status["status"] == "connected"


def test_primavera_check_connection_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PRIMAVERA_BASE_URL", "https://p6.test")
    monkeypatch.setenv("PRIMAVERA_USERNAME", "user")
    monkeypatch.setenv("PRIMAVERA_PASSWORD", "pass")

    def fake_get(url: str, *, auth: Any, timeout: float) -> httpx.Response:
        raise httpx.HTTPStatusError("bad", request=httpx.Request("GET", url), response=_response(url, status_code=503))

    monkeypatch.setattr(primavera.httpx, "get", fake_get)
    status = primavera.check_connection()
    assert status["status"] == "stubbed"
    assert "activities" in status["details"]


def test_bim_check_connection_success(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("BIM_BASE_URL", "https://bim.test")
    monkeypatch.setenv("BIM_AUTH_TOKEN", "token")

    def fake_get(url: str, *, headers: Dict[str, str], timeout: float) -> httpx.Response:
        assert headers["Authorization"].startswith("Bearer ")
        return _response(url, json_body={"status": "ok"})

    monkeypatch.setattr(bim.httpx, "get", fake_get)
    status = bim.check_connection()
    assert status["status"] == "connected"


def test_bim_check_connection_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("BIM_BASE_URL", "https://bim.test")
    monkeypatch.setenv("BIM_AUTH_TOKEN", "token")

    def fake_get(url: str, *, headers: Dict[str, str], timeout: float) -> httpx.Response:
        raise httpx.ConnectTimeout("timeout", request=httpx.Request("GET", url))

    monkeypatch.setattr(bim.httpx, "get", fake_get)
    status = bim.check_connection()
    assert status["status"] == "error"


def test_vision_check_connection_success(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("VISION_BASE_URL", "https://vision.test")
    monkeypatch.setenv("VISION_API_KEY", "token")

    def fake_get(url: str, *, headers: Dict[str, str], timeout: float) -> httpx.Response:
        assert headers["Authorization"].startswith("Bearer ")
        return _response(url, json_body={"status": "ok"})

    monkeypatch.setattr(vision.httpx, "get", fake_get)
    status = vision.check_connection()
    assert status["status"] == "connected"


def test_vision_check_connection_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("VISION_BASE_URL", "https://vision.test")
    monkeypatch.setenv("VISION_API_KEY", "token")

    def fake_get(url: str, *, headers: Dict[str, str], timeout: float) -> httpx.Response:
        raise httpx.HTTPStatusError("bad", request=httpx.Request("GET", url), response=_response(url, status_code=500))

    monkeypatch.setattr(vision.httpx, "get", fake_get)
    status = vision.check_connection()
    assert status["status"] == "error"


def test_connectors_list_success(client: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ONEDRIVE_HEALTH_URL", "https://onedrive.test/health")
    monkeypatch.setenv("POWER_BI_HEALTH_URL", "https://powerbi.test/health")
    monkeypatch.setenv("TEAMS_HEALTH_URL", "https://teams.test/health")

    def fake_get(url: str, **_: Any) -> httpx.Response:  # type: ignore[override]
        return _response(url, json_body={"status": "ok"})

    monkeypatch.setattr(connectors.httpx, "get", fake_get)
    monkeypatch.setattr(connectors.google_drive, "drive_credentials_available", lambda: True)
    monkeypatch.setattr(connectors.google_drive, "drive_stubbed", lambda: False)
    monkeypatch.setattr(connectors.google_drive, "drive_service_error", lambda: None)
    monkeypatch.setattr("backend.api.connectors.bim_status", lambda: {"service": "bim", "status": "connected"})
    monkeypatch.setattr("backend.api.connectors.primavera_status", lambda: {"service": "p6", "status": "connected"})
    monkeypatch.setattr("backend.api.connectors.aconex_status", lambda: {"service": "aconex", "status": "connected"})
    monkeypatch.setattr("backend.api.connectors.vision_status", lambda: {"service": "vision", "status": "connected"})

    response = client.get("/api/connectors/list")
    data = response.json()
    assert data["google_drive"]["status"] == "connected"
    assert data["onedrive"]["status"] == "connected"
    assert data["teams"]["status"] == "connected"
    assert data["power_bi"]["status"] == "connected"
    assert data["photo"]["service"] == "photo"


def test_connectors_list_failure(client: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ONEDRIVE_HEALTH_URL", raising=False)
    monkeypatch.delenv("POWER_BI_HEALTH_URL", raising=False)
    monkeypatch.delenv("TEAMS_HEALTH_URL", raising=False)
    monkeypatch.delenv("TEAMS_WEBHOOK_URL", raising=False)

    monkeypatch.setattr(connectors.google_drive, "drive_credentials_available", lambda: False)
    monkeypatch.setattr(connectors.google_drive, "drive_stubbed", lambda: True)
    monkeypatch.setattr(connectors.google_drive, "drive_service_error", lambda: "missing credentials")
    monkeypatch.setattr("backend.api.connectors.bim_status", lambda: {"service": "bim", "status": "error"})
    monkeypatch.setattr("backend.api.connectors.primavera_status", lambda: {"service": "p6", "status": "error"})
    monkeypatch.setattr("backend.api.connectors.aconex_status", lambda: {"service": "aconex", "status": "error"})
    monkeypatch.setattr("backend.api.connectors.vision_status", lambda: {"service": "vision", "status": "error"})

    response = client.get("/api/connectors/list")
    data = response.json()
    assert data["google_drive"]["status"] == "error"
    assert data["onedrive"]["status"] == "unconfigured"
    assert data["teams"]["status"] == "unconfigured"
    assert data["power_bi"]["status"] == "unconfigured"
    assert data["photo"]["status"] == "error"
