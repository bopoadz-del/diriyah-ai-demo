"""Chat endpoints backed by the in-memory stub store."""

from __future__ import annotations

from typing import Any, Dict

from fastapi import APIRouter, HTTPException

from backend.services import stub_state

router = APIRouter()


@router.get("/projects/{project_id}/chats")
def list_chats(project_id: str) -> list[Dict[str, Any]]:
    return stub_state.list_chats(project_id)


@router.post("/projects/{project_id}/chats")
def create_chat(project_id: str) -> Dict[str, Any]:
    try:
        chat = stub_state.create_chat(project_id)
    except KeyError as exc:  # pragma: no cover - defensive for misconfigured ids
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return chat


@router.put("/chats/{chat_id}/rename")
def rename_chat(chat_id: int, title: str) -> Dict[str, Any]:
    chat = stub_state.rename_chat(chat_id, title=title)
    if chat is None:
        raise HTTPException(status_code=404, detail="Chat not found")
    return {"status": "ok", "chat": chat}


@router.put("/chats/{chat_id}/pin")
def pin_chat(chat_id: int) -> Dict[str, Any]:
    chat = stub_state.pin_chat(chat_id, pinned=True)
    if chat is None:
        raise HTTPException(status_code=404, detail="Chat not found")
    return {"status": "ok", "chat": chat}


@router.put("/chats/{chat_id}/unpin")
def unpin_chat(chat_id: int) -> Dict[str, Any]:
    chat = stub_state.pin_chat(chat_id, pinned=False)
    if chat is None:
        raise HTTPException(status_code=404, detail="Chat not found")
    return {"status": "ok", "chat": chat}
