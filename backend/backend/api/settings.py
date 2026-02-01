from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..db import get_db
from .. import models

router = APIRouter()


@router.get("/projects/{project_id}/settings")
def get_settings(project_id: int, db: Session = Depends(get_db)):
    project = db.get(models.Project, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    return {"id": project.id, "name": project.name}


@router.put("/projects/{project_id}/settings")
def update_settings(project_id: int, name: str, db: Session = Depends(get_db)):
    project = db.get(models.Project, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    project.name = name
    db.commit()
    return project