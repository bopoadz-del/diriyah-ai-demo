from __future__ import annotations
from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.api import users  # noqa: E402

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
        projects=[101, 202, 303],
    ).model_dump()

def test_update_user_returns_stub_acknowledgement() -> None:
    response = client.post("/api/users/update")
    assert response.status_code == 200
    assert response.json() == users.UpdateAck(
        status="ok", message="Updated (stub)"
    ).model_dump()

def test_main_registers_users_router() -> None:
    from backend.main import app as main_app

    paths = {route.path for route in main_app.router.routes}
    assert "/api/users/me" in paths
    assert "/api/users/update" in paths
