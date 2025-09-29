from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from ..db import get_db
from .. import models
from ..services.analytics_service import log_action
import os
from openai import OpenAI

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY")) if os.getenv("OPENAI_API_KEY") else None
router = APIRouter()

def _heuristic_title(text: str) -> str:
    txt = " ".join(text.strip().split())
    if not txt:
        return "New Chat"
    return " ".join(txt.split()[:6])[:60].title()

def _auto_title_from_first_message(content: str) -> str:
    if client:
        try:
            prompt = f"Suggest a short, specific 3–7 word title:\n{content}\nTitle:"
            resp = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role":"user","content":prompt}],
                temperature=0.2
            )
            t = resp.choices[0].message.content.strip().strip('"')
            if 3 <= len(t.split()) <= 10:
                return t[:80]
        except Exception:
            pass
    return _heuristic_title(content)

@router.get("/chats/{chat_id}/messages")
def list_messages(chat_id: int, db: Session = Depends(get_db)):
    return db.query(models.Message)             .filter(models.Message.chat_id == chat_id)             .order_by(models.Message.created_at.asc())             .all()

@router.post("/chats/{chat_id}/messages")
def create_message(chat_id: int, role: str, content: str, db: Session = Depends(get_db)):
    msg = models.Message(chat_id=chat_id, role=role, content=content)
    db.add(msg); db.commit(); db.refresh(msg)

    if role == "user":
        cnt = db.query(models.Message).filter(models.Message.chat_id == chat_id).count()
        if cnt == 1:
            chat = db.query(models.Chat).get(chat_id)
            chat.title = _auto_title_from_first_message(content)
            db.commit()
    return msg

@router.put("/messages/{msg_id}/action")
def message_action(msg_id: int, action: str, user_id: int = 1, db: Session = Depends(get_db)):
    msg = db.query(models.Message).get(msg_id)
    if action == "like": msg.liked = True
    elif action == "dislike": msg.disliked = True
    elif action == "copy": msg.copied = True
    elif action == "read": msg.read = True
    log_action(db, user_id=user_id, action=action, message_id=msg_id)
    db.commit()
    return msg

@router.put("/messages/{msg_id}")
def update_message(msg_id: int, content: str, db: Session = Depends(get_db)):
    msg = db.query(models.Message).get(msg_id)
    msg.content = content
    db.commit()
    return msg