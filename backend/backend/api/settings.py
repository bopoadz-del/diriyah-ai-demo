from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from ..db import get_db
from .. import models

router = APIRouter()

@router.get("/projects/{project_id}/settings")
def get_settings(project_id: int, db: Session = Depends(get_db)):
    project = db.query(models.Project).get(project_id)
    return {"id": project.id, "name": project.name}

@router.put("/projects/{project_id}/settings")
def update_settings(project_id: int, name: str, db: Session = Depends(get_db)):
    project = db.query(models.Project).get(project_id)
    project.name = name; db.commit()
    return project