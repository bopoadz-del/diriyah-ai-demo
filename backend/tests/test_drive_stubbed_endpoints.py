from __future__ import annotations

from fastapi.testclient import TestClient

from backend.main import app


def test_drive_scan_returns_stubbed_projects() -> None:
    with TestClient(app) as client:
        response = client.get("/api/projects/scan-drive")
        assert response.status_code == 200
        payload = response.json()
    assert "projects" in payload
    assert isinstance(payload["projects"], list)
    assert payload["projects"], "expected stubbed projects to be returned"


def test_drive_diagnose_reports_error_when_stubbed() -> None:
    with TestClient(app) as client:
        response = client.get("/api/drive/diagnose")
        assert response.status_code == 200
        payload = response.json()
    assert payload.get("status") == "error"
    assert "detail" in payload
