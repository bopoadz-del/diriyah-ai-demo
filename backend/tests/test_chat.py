codex/update-active-project-storage-structure

"""Tests for the chat endpoint to ensure active project handling."""

 main
from collections.abc import Generator

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

codex/update-active-project-storage-structure
from backend.api import chat
from backend.services.vector_memory import set_active_project


@pytest.fixture()
def client() -> Generator[TestClient, None, None]:
    """Provide a lightweight FastAPI test client with only the chat router."""

    app = FastAPI()
    app.include_router(chat.router, prefix="/api")


from backend.api.chat import router as chat_router
from backend.services.vector_memory import set_active_project


class _MockCollection:
    """Predictable collection used to validate chat integration."""

 codex/add-tests-for-active-project-in-chat
    def __init__(self) -> None:
        self.calls = []

    def query(self, *, query_texts, n_results):  # pragma: no cover - simple stub
        self.calls.append({"query_texts": query_texts, "n_results": n_results})

    def __init__(self):
codex/add-tests-for-active-project-in-chat-y0qgyr
        self.queries: list[dict[str, object]] = []

    def query(self, *, query_texts, n_results):  # pragma: no cover - simple stub
        """Record the provided arguments and emit deterministic documents."""


        self.queries = []
 codex/update-vector_memory-to-handle-project-payload
    def query(self, *, query_texts, n_results):  # pragma: no cover - simple stub

 codex/add-tests-for-active-project-in-chat-ojreow
    def query(self, *, query_texts, n_results):  # pragma: no cover - simple stub

codex/add-tests-for-active-project-in-chat-nr6q6k
    def query(self, *, query_texts, n_results):  # pragma: no cover - simple stub

    def query(self, query_texts, n_results):  # pragma: no cover - simple stub
 main
 main
 main
 main
        self.queries.append({"query_texts": query_texts, "n_results": n_results})
main
        return {"documents": [["Doc snippet"]]}


@pytest.fixture()
def client():
    app = FastAPI()
    app.include_router(chat_router, prefix="/api") 
       main
    with TestClient(app) as test_client:
        yield test_client


def test_chat_without_active_project(client):
 codex/update-active-project-storage-structure
    """Chat endpoint should respond gracefully when no project is selected."""

    set_active_project(None)

    response = client.post("/api/chat", data={"message": "hello"})

    """Chat endpoint should handle missing active project gracefully."""

    set_active_project(None)
    response = client.post("/api/chat", data={"message": "Hello"})
    assert response.status_code == 200
    payload = response.json()
    assert payload["project_id"] is None
 codex/update-vector_memory-to-handle-project-payload
    if "intent" in payload:
        assert payload["intent"]["project_id"] is None

    assert payload.get("context_docs", []) == []
    assert payload["intent"]["project_id"] is None

 main


codex/update-vector_memory-to-handle-project-payload
def test_chat_with_active_project_collection(client):
    """When an active project includes a collection, results are surfaced."""

    set_active_project({"id": "proj-123", "collection": _MockCollection()})

    class EmptyDocumentsCollection:
        def query(self, *, query_texts, n_results):  # pragma: no cover - simple stub
            return {"documents": []}

    set_active_project({"id": "proj-123", "collection": EmptyDocumentsCollection()})
    try:
        response = client.post("/api/chat", data={"message": "Hello"})
    finally:
        set_active_project(None)

codex/add-tests-for-active-project-in-chat
    try:
        response = client.post("/api/chat", data={"message": "Hello"})
    finally:
        set_active_project(None)
 main
 main

    assert response.status_code == 200

    payload = response.json()
 codex/update-active-project-storage-structure
    assert payload["project_id"] is None
    assert payload["context_docs"] == []
    assert payload["intent"]["intent"] == "unknown"

    assert payload.get("context_docs", []) == []


def test_chat_with_active_project_collection(client):
    """Chat endpoint should return project context when collection is active."""

    collection = _MockCollection()
    set_active_project({"id": "proj-123", "collection": collection})

 codex/add-tests-for-active-project-in-chat-ojreow
 main

    try:
        response = client.post("/api/chat", data={"message": "Hello"})
    finally:
        set_active_project(None)

 codex/add-tests-for-active-project-in-chat
    assert response.status_code == 200

    payload = response.json()
    assert payload["project_id"] == "proj-123"
    assert payload["context_docs"] == ["Doc snippet"]
    assert "proj-123" in payload["response"]
    assert collection.calls == [{"query_texts": ["Hello"], "n_results": 3}]

 main
    assert response.status_code == 200
    payload = response.json()
    assert payload["project_id"] == "proj-123"
    if "context_docs" in payload:
        assert payload["context_docs"] == ["Doc snippet"]
    assert "proj-123" in payload["response"]


def test_chat_with_empty_documents(client):
    """Chat endpoint should handle empty document results gracefully."""

    class EmptyDocumentsCollection:
        def query(self, *, query_texts, n_results):  # pragma: no cover - simple stub
            return {"documents": []}

    set_active_project({"id": "proj-123", "collection": EmptyDocumentsCollection()})

    response = client.post("/api/chat", data={"message": "Hello"})
    assert response.status_code == 200

    payload = response.json()
 codex/update-vector_memory-to-handle-project-payload
    assert payload["context_docs"] == []

    assert payload["project_id"] == "proj-123"
    assert payload["context_docs"] == ["Doc snippet"]
 codex/add-tests-for-active-project-in-chat-y0qgyr
    assert "proj-123" in payload["response"]

    assert payload["response"].endswith("proj-123") main
    assert collection.queries == [{"query_texts": ["Hello"], "n_results": 3}]
 main
main
      main
