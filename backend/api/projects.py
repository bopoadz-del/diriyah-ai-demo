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


@router.get("/projects", response_model=List[ProjectStub])
def list_projects() -> List[ProjectStub]:
    """Return an empty list until real project data is wired up."""

    return []
