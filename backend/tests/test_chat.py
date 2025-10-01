<<<<<<< HEAD
"""Tests for the chat endpoint to ensure active project handling."""

from collections.abc import Generator

import pytest

from backend.services.vector_memory import set_active_project


@pytest.fixture(autouse=True)
def reset_active_project() -> Generator[None, None, None]:
    """Ensure each test starts with no active project configured."""

    set_active_project()
    yield
    set_active_project()


def test_chat_without_active_project(client):
    """The chat endpoint should respond even when no project is selected."""

    response = client.post("/api/chat", data={"message": "Hello"})
    assert response.status_code == 200
    payload = response.json()
    assert payload["project_id"] is None
    assert isinstance(payload["response"], str) and payload["response"].startswith("AI response")


class _MockCollection:
    def query(self, *, query_texts, n_results):
        assert query_texts == ["Hello"]
        assert n_results == 3
        return {"documents": [["Doc snippet"]]}


def test_chat_with_active_project_collection(client):
    """When an active project includes a collection, results are surfaced."""

    set_active_project({"id": "proj-123", "collection": _MockCollection()})

    response = client.post("/api/chat", data={"message": "Hello"})
    assert response.status_code == 200
    payload = response.json()
    assert payload["project_id"] == "proj-123"
    assert payload["context_docs"] == ["Doc snippet"]
    assert "proj-123" in payload["response"]
=======
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
>>>>>>> origin/main
