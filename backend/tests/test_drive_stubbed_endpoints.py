from __future__ import annotations

from fastapi.testclient import TestClient

from backend.main import app


def test_drive_scan_returns_projects_from_drive_wrapper() -> None:
    with TestClient(app, headers={"X-Tenant-ID": "test-tenant"}) as client:
        response = client.get("/api/projects/scan-drive")
        assert response.status_code == 200
        payload = response.json()
    assert payload.get("projects"), "expected drive projects to be returned"
    assert payload.get("status") in {"ok", "stubbed"}


def test_drive_scan_projects_include_debug_metadata() -> None:
    with TestClient(app, headers={"X-Tenant-ID": "test-tenant"}) as client:
        response = client.get("/api/projects/scan-drive")
        assert response.status_code == 200
        payload = response.json()

    assert payload.get("detail")

    for project in payload.get("projects", []):
        assert isinstance(project["name"], str) and project["name"], "missing name"
        assert isinstance(project["path"], str) and project["path"], "missing path"
        assert "last_modified" in project and project["last_modified"], "missing last_modified"
        assert project.get("source") in {"google_drive", "stubbed"}


def test_drive_diagnose_reports_error_when_stubbed() -> None:
    with TestClient(app, headers={"X-Tenant-ID": "test-tenant"}) as client:
        response = client.get("/api/drive/diagnose")
        assert response.status_code == 200
        payload = response.json()
    assert payload.get("status") == "error"
    assert "detail" in payload
