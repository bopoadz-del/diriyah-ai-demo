"""Message endpoints for the stubbed chat experience."""

from __future__ import annotations

from typing import Any, Dict

from fastapi import APIRouter, HTTPException

from backend.services import stub_state

router = APIRouter()


@router.get("/chats/{chat_id}/messages")
def list_messages(chat_id: int) -> list[Dict[str, Any]]:
    return stub_state.list_messages(chat_id)


@router.post("/chats/{chat_id}/messages")
def create_message(chat_id: int, role: str, content: str) -> Dict[str, Any]:
    chat = stub_state.get_chat(chat_id)
    if chat is None:
        raise HTTPException(status_code=404, detail="Chat not found")
    message = stub_state.add_message(chat_id, role=role, content=content)
    return message


@router.put("/messages/{message_id}")
def update_message(message_id: int, content: str) -> Dict[str, Any]:
    message = stub_state.update_message(message_id, content=content)
    if message is None:
        raise HTTPException(status_code=404, detail="Message not found")
    return message


@router.put("/messages/{message_id}/action")
def message_action(message_id: int, action: str, user_id: int = 1) -> Dict[str, Any]:
    message = stub_state.apply_message_action(message_id, action=action, user_id=user_id)
    if message is None:
        raise HTTPException(status_code=404, detail="Message not found")
    return message
