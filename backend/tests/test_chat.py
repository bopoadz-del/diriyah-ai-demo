"""Tests for the chat endpoint to ensure active project handling."""

from collections.abc import Generator

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.api.chat import router as chat_router
from backend.services.vector_memory import set_active_project


@pytest.fixture()
def client() -> Generator[TestClient, None, None]:
    """Provide a lightweight FastAPI test client with only the chat router."""

    app = FastAPI()
    app.include_router(chat_router, prefix="/api")

    with TestClient(app) as test_client:
        yield test_client


class _MockCollection:
    """Predictable collection used to validate chat integration."""

    def __init__(self) -> None:
        self.queries: list[dict[str, object]] = []

    def query(self, *, query_texts, n_results):  # pragma: no cover - simple stub
        """Record the provided arguments and emit deterministic documents."""

        self.queries.append({"query_texts": query_texts, "n_results": n_results})
        return {"documents": [["Doc snippet"]]}


def test_chat_without_active_project(client: TestClient) -> None:
    """Chat endpoint should respond gracefully when no project is selected."""

    set_active_project(None)

    response = client.post("/api/chat", data={"message": "Hello"})

    assert response.status_code == 200

    payload = response.json()
    assert payload["project_id"] is None
    assert payload["context_docs"] == []
    assert payload["intent"]["project_id"] is None


def test_chat_with_active_project_collection(client: TestClient) -> None:
    """When an active project includes a collection, results are surfaced."""

    collection = _MockCollection()
    set_active_project({"id": "proj-123", "collection": collection})

    try:
        response = client.post("/api/chat", data={"message": "Hello"})
    finally:
        set_active_project(None)

    assert response.status_code == 200

    payload = response.json()
    assert payload["project_id"] == "proj-123"
    assert payload["context_docs"] == ["Doc snippet"]
    assert "proj-123" in payload["response"]
    assert collection.queries == [{"query_texts": ["Hello"], "n_results": 3}]


def test_chat_with_empty_documents(client: TestClient) -> None:
    """Chat endpoint should handle empty document results gracefully."""

    class EmptyDocumentsCollection:
        def query(self, *, query_texts, n_results):  # pragma: no cover - simple stub
            return {"documents": []}

    set_active_project({"id": "proj-123", "collection": EmptyDocumentsCollection()})

    try:
        response = client.post("/api/chat", data={"message": "Hello"})
    finally:
        set_active_project(None)

    assert response.status_code == 200

    payload = response.json()
    assert payload["project_id"] == "proj-123"
    assert payload["context_docs"] == []
