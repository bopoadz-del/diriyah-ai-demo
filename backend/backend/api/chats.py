from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from ..db import get_db
from .. import models

router = APIRouter()

@router.get("/projects/{project_id}/chats")
def list_chats(project_id: int, db: Session = Depends(get_db)):
    return db.query(models.Chat)             .filter(models.Chat.project_id == project_id)             .order_by(models.Chat.pinned.desc(), models.Chat.created_at.desc())             .all()

@router.post("/projects/{project_id}/chats")
def create_chat(project_id: int, db: Session = Depends(get_db)):
    chat = models.Chat(project_id=project_id, title="New Chat")
    db.add(chat)
    db.commit()
    db.refresh(chat)
    return chat

@router.put("/chats/{chat_id}/rename")
def rename_chat(chat_id: int, title: str, db: Session = Depends(get_db)):
    chat = db.query(models.Chat).get(chat_id)
    chat.title = title
    db.commit()
    return chat

@router.put("/chats/{chat_id}/pin")
def pin_chat(chat_id: int, db: Session = Depends(get_db)):
    chat = db.query(models.Chat).get(chat_id)
    chat.pinned = True
    db.commit()
    return chat

@router.put("/chats/{chat_id}/unpin")
def unpin_chat(chat_id: int, db: Session = Depends(get_db)):
    chat = db.query(models.Chat).get(chat_id)
    chat.pinned = False
    db.commit()
    return chat