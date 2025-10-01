from __future__ import annotations

from fastapi.testclient import TestClient

from backend.api.projects import _PROJECTS
from backend.main import app


def test_projects_endpoint_returns_stubbed_payload() -> None:
    with TestClient(app) as client:
        response = client.get("/api/projects")
        assert response.status_code == 200
        payload = response.json()
    expected = [project.model_dump() for project in _PROJECTS]
    assert payload == expected
