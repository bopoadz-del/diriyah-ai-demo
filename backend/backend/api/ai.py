import importlib
import os

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from .. import models
from ..db import get_db
from ..services.intent_router import route_intent
from ..services.rag_service import add_document

router = APIRouter()
_openai_client = None
_openai_available = True


def _get_openai_client():
    global _openai_client, _openai_available
    if _openai_client is not None or not _openai_available:
        return _openai_client
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        _openai_available = False
        return None
    try:
        openai_module = importlib.import_module("openai")
        OpenAI = getattr(openai_module, "OpenAI", None)
        if OpenAI is None:
            _openai_available = False
            return None
        _openai_client = OpenAI(api_key=api_key)
    except Exception:
        _openai_available = False
        return None
    return _openai_client

@router.post("/ai/query")
def ai_query(project_id: str, query: str):
    return {"answer": route_intent(project_id, query)}

@router.post("/ai/add")
def ai_add(project_id: str, text: str, source: str = "manual"):
    add_document(project_id, text, source)
    return {"status": "indexed"}

@router.post("/ai/summarize")
def ai_summarize(chat_id: int, db: Session = Depends(get_db)):
    msgs = db.query(models.Message)             .filter(models.Message.chat_id == chat_id)             .order_by(models.Message.created_at.asc()).all()
    convo = "\n".join([f"{m.role.upper()}: {m.content}" for m in msgs]) or "(empty)"
    client = _get_openai_client()
    if client:
        try:
            prompt = f"Summarize the chat in 5–8 bullets with dates if present:\n\n{convo}"
            resp = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role":"user","content":prompt}],
                temperature=0.2
            )
            return {"summary": resp.choices[0].message.content.strip()}
        except Exception:
            pass
    head = msgs[0].content if msgs else ""
    tail = msgs[-1].content if msgs else ""
    return {"summary": f"- Started: {head[:120]}\n- Latest: {tail[:120]}\n- Messages: {len(msgs)}"}
