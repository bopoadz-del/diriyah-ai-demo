from __future__ import annotations

from datetime import datetime, timezone
from typing import List

from fastapi import APIRouter
from pydantic import BaseModel, Field

router = APIRouter()


class DriveScanProject(BaseModel):
    """Represents a single project discovered during a drive scan."""

    name: str = Field(..., description="Display name of the project folder")
    path: str = Field(..., description="Absolute path to the project folder on disk")
    last_modified: datetime = Field(
        ..., description="Timestamp representing the most recent modification time"
    )
    source: str = Field(
        "stubbed", description="Identifier for the provider that surfaced the project"
    )


class DriveScanResponse(BaseModel):
    """Response schema returned when scanning the drive for project folders."""

    status: str = Field(
        "stubbed", description="Drive scan status indicating no real scan was performed"
    )
    detail: str = Field(
        "Drive scanning is currently stubbed for development and tests.",
        description="Additional information about the stubbed response",
    )
    projects: List[DriveScanProject] = Field(
        default_factory=list,
        description="Collection of project folders discovered on the drive",
    )


_STUBBED_PROJECTS: list[DriveScanProject] = [
    DriveScanProject(
        name="Gateway Villas",
        path="/Volumes/Diriyah/Projects/Gateway Villas",
        last_modified=datetime(2024, 1, 15, 9, 30, tzinfo=timezone.utc),
    ),
    DriveScanProject(
        name="Downtown Towers",
        path="/Volumes/Diriyah/Projects/Downtown Towers",
        last_modified=datetime(2024, 3, 8, 17, 5, tzinfo=timezone.utc),
    ),
    DriveScanProject(
        name="Cultural District",
        path="/Volumes/Diriyah/Projects/Cultural District",
        last_modified=datetime(2023, 11, 21, 13, 42, tzinfo=timezone.utc),
    ),
]


@router.get("/projects/scan-drive")
def scan_drive_for_projects() -> DriveScanResponse:
    """Return a deterministic stubbed list of project folders."""

    return DriveScanResponse(projects=_STUBBED_PROJECTS)


@router.get("/drive/scan/status")
def drive_scan_status() -> dict[str, str]:
    """Return a stubbed response representing drive scanning state."""

    return {"status": "idle", "detail": "Drive scanning is not available in tests"}
