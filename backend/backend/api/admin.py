from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from ..db import get_db
from .. import models

router = APIRouter()

@router.get("/users")
def list_users(db: Session = Depends(get_db)):
    return db.query(models.User).all()

@router.post("/users")
def create_user(name: str, email: str, role: str = "user", db: Session = Depends(get_db)):
    u = models.User(name=name, email=email, role=role)
    db.add(u); db.commit(); db.refresh(u)
    return u

@router.put("/users/{user_id}/role")
def set_role(user_id: int, role: str, db: Session = Depends(get_db)):
    u = db.query(models.User).get(user_id)
    u.role = role; db.commit()
    return u