from __future__ import annotations

from typing import List

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()


class ProjectStub(BaseModel):
    """Minimal project representation used for local development."""

    id: int
    name: str
    status: str


_PROJECTS: List[ProjectStub] = [
    ProjectStub(id=1, name="Gateway Villas", status="active"),
    ProjectStub(id=2, name="Downtown Towers", status="planning"),
    ProjectStub(id=3, name="Cultural District", status="on-hold"),
]


@router.get("/projects", response_model=List[ProjectStub])
def list_projects() -> List[ProjectStub]:
    """Return a deterministic set of stubbed projects for the UI."""

    return _PROJECTS
