from __future__ import annotations
import os
from pathlib import Path
import sys
from fastapi import FastAPI
from fastapi.testclient import TestClient

# Ensure project root on path
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.api import projects  # noqa: E402

TEST_APP = FastAPI()
TEST_APP.include_router(projects.router, prefix="/api")
client = TestClient(TEST_APP)

def test_fixture_mode_enabled() -> None:
    assert os.getenv("USE_FIXTURE_PROJECTS") == "true"

def test_list_projects_returns_fixture_order() -> None:
    response = client.get("/api/projects")
    assert response.status_code == 200
    assert response.json() == list(projects.PROJECT_FIXTURES.values())

def test_get_project_returns_expected_stub() -> None:
    project_id, project_stub = next(iter(projects.PROJECT_FIXTURES.items()))
    response = client.get(f"/api/projects/{project_id}")
    assert response.status_code == 200
    assert response.json() == project_stub

def test_get_project_unknown_id_returns_404() -> None:
    response = client.get("/api/projects/unknown")
    assert response.status_code == 404
    assert response.json()["detail"] == "Project not found"
