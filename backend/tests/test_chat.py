import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.api.chat import router as chat_router
from backend.services.vector_memory import set_active_project


@pytest.fixture()
def client():
    app = FastAPI()
    app.include_router(chat_router, prefix="/api")
    with TestClient(app) as test_client:
        yield test_client


def test_chat_without_active_project(client):
    """Chat endpoint should handle missing active project gracefully."""

    set_active_project(None)

    response = client.post("/api/chat", data={"message": "Hello"})
    assert response.status_code == 200

    payload = response.json()
    assert payload["project_id"] is None
    assert payload["intent"]["project_id"] is None
