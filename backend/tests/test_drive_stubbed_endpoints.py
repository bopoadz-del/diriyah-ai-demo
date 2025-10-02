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


def test_drive_scan_projects_include_debug_metadata() -> None:
    with TestClient(app) as client:
        response = client.get("/api/projects/scan-drive")
        assert response.status_code == 200
        payload = response.json()

    assert payload.get("status") == "stubbed"
    assert payload.get("detail")

    for project in payload.get("projects", []):
        assert isinstance(project["name"], str) and project["name"], "missing name"
        assert isinstance(project["path"], str) and project["path"], "missing path"
        assert "last_modified" in project and project["last_modified"], "missing last_modified"
        assert project.get("source") == "stubbed"


def test_drive_diagnose_reports_error_when_stubbed() -> None:
    with TestClient(app) as client:
        response = client.get("/api/drive/diagnose")
        assert response.status_code == 200
        payload = response.json()
    assert payload.get("status") == "error"
    assert "detail" in payload
