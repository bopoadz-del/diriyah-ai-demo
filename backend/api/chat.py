from collections.abc import Mapping
from typing import Any, Optional
from urllib.parse import parse_qs

from fastapi import APIRouter, Body, Form, HTTPException, Request

try:  # pragma: no cover - optional multipart dependency
    import multipart  # type: ignore
except ModuleNotFoundError:  # pragma: no cover - handled gracefully
    multipart = None  # type: ignore[assignment]

_message_dependency = Form(None) if multipart is not None else Body(None)

from backend.services.intent_router import IntentRouter
from backend.services.vector_memory import get_active_project

router = APIRouter()
intent_router = IntentRouter()


@router.post("/chat")
async def chat(request: Request, message: Optional[str] = _message_dependency) -> dict[str, Any]:
    """Respond to chat messages while respecting the active project context."""

    content_type = request.headers.get("content-type", "")
    if "application/json" in content_type:
        try:
            payload = await request.json()
        except Exception:
            payload = None
        if isinstance(payload, Mapping):
            potential = payload.get("message")
            if isinstance(potential, str):
                message = potential
    else:
        if multipart is None:
            try:
                raw_body = (await request.body()).decode("utf-8")
            except Exception:
                raw_body = ""
            parsed = parse_qs(raw_body)
            values = parsed.get("message")
            if values and isinstance(values, list):
                first = values[0]
                if isinstance(first, str):
                    message = first
        else:
            try:
                form = await request.form()
            except Exception:
                form = None
            if form is not None:
                potential = form.get("message")
                if isinstance(potential, str):
                    message = potential

    if not message:
        raise HTTPException(status_code=400, detail="message parameter is required")

    active = get_active_project()
    project_id = None
    collection = None

    if isinstance(active, Mapping):
        project_id = active.get("id")
        collection = active.get("collection")
    elif active is not None:
        project_id = getattr(active, "id", None)
        collection = getattr(active, "collection", None)

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
