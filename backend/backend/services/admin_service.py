from sqlalchemy.orm import Session
from ..db import SessionLocal
from .. import models

def handle_admin_request(query: str) -> str:
    db: Session = SessionLocal()
    q = query.lower()
    if "add user" in q:
        u = models.User(name="AutoUser", email="auto@example.com", role="user")
        db.add(u); db.commit()
        return "User AutoUser added."
    if "list users" in q:
        users = db.query(models.User).all()
        return "\n".join([f"{u.id}: {u.name} ({u.role})" for u in users])
    return f"[Admin Service] Executed: {query}"