from collections.abc import Mapping
from typing import Any

from fastapi import APIRouter, Form

from backend.services.intent_router import IntentRouter
from backend.services.vector_memory import get_active_project

router = APIRouter()
intent_router = IntentRouter()


@router.post("/chat")
async def chat(message: str = Form(...)) -> dict[str, Any]:
    """Respond to chat messages while respecting the active project context."""

    active = get_active_project() or {}
    if not isinstance(active, Mapping):
        active = {}

    project_id = active.get("id")
    collection = active.get("collection")

    intent_result = intent_router.route(message, project_id=project_id)

    context_docs: list[str] = []
    if collection and hasattr(collection, "query"):
        try:
            result = collection.query(query_texts=[message], n_results=3)
            if isinstance(result, Mapping):
                documents = result.get("documents")
                if isinstance(documents, list) and documents:
                    first_entry = documents[0]
                    if isinstance(first_entry, list):
                        context_docs = first_entry
                    elif first_entry is None:
                        context_docs = []
                    else:
                        context_docs = [first_entry]
        except Exception:  # pragma: no cover - defensive guard
            context_docs = []

    return {
        "intent": intent_result,
        "project_id": project_id,
        "context_docs": context_docs,
        "response": f"AI response for project {project_id or 'none'}",
    }
