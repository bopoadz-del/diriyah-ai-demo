"""Stubbed AI endpoints that power the chat demo."""

from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from backend.api.projects import PROJECT_FIXTURES
from backend.services import stub_state

router = APIRouter()


class QueryRequest(BaseModel):
    project_id: Optional[str] = Field(default=None, description="Active project identifier")
    query: str


class QueryResponse(BaseModel):
    status: str
    answer: str
    project: Optional[Dict[str, Any]] = None


class SummariseRequest(BaseModel):
    chat_id: int


@router.post("/ai/query", response_model=QueryResponse)
def query_ai(payload: QueryRequest) -> Dict[str, Any]:
    project = stub_state.get_project(payload.project_id) if payload.project_id else None
    if project is None and payload.project_id:
        # Fallback to fixtures so demo queries always succeed.
        project = PROJECT_FIXTURES.get(payload.project_id)
    summary = project.get("summary") if project else None
    answer_lines = [
        "Here's what I can tell so far:",
        summary or "No detailed project summary available yet.",
        f"Question asked: {payload.query}",
    ]
    answer_lines.append(
        "Suggested next step: capture any decisions in the chat log and notify the delivery team."
    )
    answer = "\n".join(answer_lines)

    stub_state.log_action(
        action="ai_query",
        user_id=1,
        detail={"project_id": payload.project_id, "query": payload.query},
    )
    return {"status": "ok", "answer": answer, "project": project}


@router.post("/ai/summarize")
def summarise_chat(payload: SummariseRequest) -> Dict[str, Any]:
    chat = stub_state.get_chat(payload.chat_id)
    if chat is None:
        raise HTTPException(status_code=404, detail="Chat not found")
    summary = stub_state.summarise_chat(payload.chat_id)
    stub_state.log_action(
        action="chat_summarised",
        user_id=1,
        detail={"chat_id": payload.chat_id, "project_id": chat.get("project_id")},
    )
    return {"status": "ok", "summary": summary}
