from __future__ import annotations
from pathlib import Path
import sys
from fastapi import FastAPI
from fastapi.testclient import TestClient

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.api import users  # noqa: E402  (import after path setup)

TEST_APP = FastAPI()
TEST_APP.include_router(users.router, prefix="/api")
client = TestClient(TEST_APP)

def test_get_current_user_returns_stub() -> None:
    response = client.get("/api/users/me")
    assert response.status_code == 200
    assert response.json() == users.UserStub(
        id=1,
        name="Test User",
        role="Engineer",
        projects=[101, 102, 103],
    ).model_dump()


def test_user_projects_are_list_of_integers() -> None:
    response = client.get("/api/users/me")
    payload = response.json()
    assert isinstance(payload["projects"], list)
    assert all(isinstance(project_id, int) for project_id in payload["projects"])

def test_update_user_returns_stub_acknowledgement() -> None:
    response = client.post("/api/users/update")
    assert response.status_code == 200
    assert response.json() == users.UpdateAck(
        status="ok", message="Updated (stub)"
    ).model_dump()

def test_main_registers_users_router() -> None:
    main_path = Path(__file__).resolve().parents[1] / "main.py"
    source = main_path.read_text(encoding="utf-8")
    assert "app.include_router(users.router" in source
