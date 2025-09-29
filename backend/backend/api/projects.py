from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from ..db import get_db
from .. import models
from ..services.drive_service import list_project_folders

router = APIRouter()

@router.get("/projects")
def list_projects(db: Session = Depends(get_db)):
    return db.query(models.Project).all()

@router.post("/projects")
def create_project(name: str, drive_id: str | None = None, db: Session = Depends(get_db)):
    q = db.query(models.Project)
    proj = None
    if drive_id:
        proj = q.filter(models.Project.drive_id == drive_id).first()
    if not proj:
        proj = q.filter(models.Project.name == name).first()
    if proj:
        proj.name = name
        if drive_id: proj.drive_id = drive_id
    else:
        proj = models.Project(name=name, drive_id=drive_id)
        db.add(proj)
    db.commit()
    db.refresh(proj)
    return proj

@router.get("/projects/sync_drive")
def sync_projects_from_drive(db: Session = Depends(get_db)):
    folders = list_project_folders()
    out = []
    for f in folders:
        proj = db.query(models.Project).filter(models.Project.drive_id == f["id"]).first()
        if not proj:
            proj = models.Project(name=f["name"], drive_id=f["id"])
            db.add(proj)
        else:
            proj.name = f["name"]
        db.commit(); db.refresh(proj)
        out.append(proj)
    return out