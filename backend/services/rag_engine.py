"""
Enterprise ‑ready RAG engine wrapper.

This module provides the FastAPI handler for the RAG (Retrieval‑Augmented
Generation) service.  It extracts the caller's project identifier and query
string from the incoming `message` and `context` objects, delegates the
actual retrieval and summarisation to the underlying RAG service in
``backend.backend.services.rag_service`` and returns a structured result.

If the underlying embedding model or OpenAI client is unavailable, the
service will gracefully degrade by returning a fallback message provided by
``rag_service.query_rag``.  All exceptions are caught and logged to
prevent leaking stack traces in the API response.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from .intent_router import router

try:
    # Import the underlying RAG implementation from the inner backend package.
    from backend.backend.services import rag_service
except Exception:
    # Fallback in case the backend service cannot be imported.  This will
    # surface at runtime when `handle_rag_engine` is invoked.
    rag_service = None  # type: ignore[assignment]

logger = logging.getLogger(__name__)


def _extract_project_id(message: Any, context: Dict[str, Any]) -> str:
    """Extract a project identifier from the message or context.

    The project ID may be passed as ``project_id`` in the context object or
    within the message payload.  If neither is provided, ``"default"`` is
    returned.  This function normalises the value to a string.

    Parameters
    ----------
    message: Any
        The incoming message payload.  May be a dict or arbitrary object.
    context: Dict[str, Any]
        Additional metadata provided by the caller, such as authentication
        context or session data.

    Returns
    -------
    str
        A string representation of the project identifier.
    """
    if isinstance(context, dict) and context.get("project_id") is not None:
        return str(context["project_id"])
    if isinstance(message, dict) and message.get("project_id") is not None:
        return str(message["project_id"])
    return "default"


def _extract_query(message: Any) -> str:
    """Derive the query string from the incoming message.

    This helper attempts to be flexible: if the message is a dictionary,
    it will look for common fields such as ``content`` or ``text``.  If the
    message is a plain string, it will be returned directly.  For any
    other type, a string representation is returned.

    Parameters
    ----------
    message: Any
        The message body from which to extract the query.

    Returns
    -------
    str
        The extracted query string.
    """
    if isinstance(message, dict):
        for key in ("content", "text", "query"):
            if key in message and message[key]:
                return str(message[key])
    if isinstance(message, str):
        return message
    # Fallback: return string representation
    return str(message)


def handle_rag_engine(message: Any, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Handle incoming messages for the RAG engine service.

    This function is registered with the intent router.  It extracts
    parameters, delegates to the RAG service and returns a structured
    response.  Any exceptions raised by the underlying service are caught
    and logged.

    Parameters
    ----------
    message: Any
        The incoming user message or payload.
    context: Optional[Dict[str, Any]]
        Optional metadata containing project information and other context.

    Returns
    -------
    Dict[str, Any]
        A dictionary containing the service name and the result.
    """
    context = context or {}
    project_id = _extract_project_id(message, context)
    query = _extract_query(message)
    try:
        if rag_service is None:
            raise RuntimeError("RAG service implementation is unavailable")
        result = rag_service.query_rag(project_id, query)
    except Exception as exc:  # pragma: no cover - log and fallback
        logger.exception("RAG engine error: %s", exc)
        result = "An error occurred while processing your request."
    return {"service": "rag_engine", "result": result}


# Register service on import
router.register(
    "rag_engine",
    [r"\brag\b", r"\bsearch\b", r"\bmemory\b"],
    handle_rag_engine,
)
