from collections.abc import Generator

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.api import chat
from backend.services.vector_memory import set_active_project


@pytest.fixture()
def client() -> Generator[TestClient, None, None]:
    """Provide a lightweight FastAPI test client with only the chat router."""

    app = FastAPI()
    app.include_router(chat.router, prefix="/api")

    with TestClient(app) as test_client:
        yield test_client


def test_chat_without_active_project(client):
    """Chat endpoint should respond gracefully when no project is selected."""

    set_active_project(None)

    response = client.post("/api/chat", data={"message": "hello"})

    assert response.status_code == 200

    payload = response.json()
    assert payload["project_id"] is None
    assert payload["context_docs"] == []
    assert payload["intent"]["intent"] == "unknown"
