from __future__ import annotations

from datetime import datetime, timezone
from typing import List

from fastapi import APIRouter
from pydantic import BaseModel, Field

from backend.services.drive_service import list_files

router = APIRouter()


class DriveScanProject(BaseModel):
    """Represents a single project discovered during a drive scan."""

    name: str = Field(..., description="Display name of the project folder")
    path: str = Field(..., description="Drive URI pointing at the folder")
    last_modified: datetime = Field(
        ..., description="Timestamp representing the most recent modification time"
    )
    source: str = Field(
        "google_drive", description="Identifier for the provider that surfaced the project"
    )


class DriveScanResponse(BaseModel):
    """Response schema returned when scanning the drive for project folders."""

    status: str = Field(
        "ok", description="Drive scan status indicating the response was generated"
    )
    detail: str = Field(
        "Projects pulled from Google Drive using the shared demo credentials.",
        description="Additional information about the scan response",
    )
    projects: List[DriveScanProject] = Field(
        default_factory=list,
        description="Collection of project folders discovered on the drive",
    )


def _normalise_project(payload: dict[str, object]) -> DriveScanProject:
    name = str(payload.get("name", "Untitled Project"))
    file_id = str(payload.get("id", "unknown"))
    modified = payload.get("modifiedTime")
    if isinstance(modified, str):
        try:
            last_modified = datetime.fromisoformat(modified.replace("Z", "+00:00"))
        except ValueError:
            last_modified = datetime.now(timezone.utc)
    else:
        last_modified = datetime.now(timezone.utc)
    source = "stubbed" if file_id.startswith("stub-") else payload.get("source", "google_drive")
    return DriveScanProject(
        name=name,
        path=f"drive://{file_id}",
        last_modified=last_modified,
        source=str(source),
    )


@router.get("/projects/scan-drive")
def scan_drive_for_projects() -> DriveScanResponse:
    """Return Drive folders surfaced by the Google Drive wrapper."""

    files = list_files()
    projects = [_normalise_project(item) for item in files]
    detail = "Returned stubbed Google Drive folders" if any(
        project.source == "stubbed" for project in projects
    ) else "Projects pulled from Google Drive"
    status = "stubbed" if any(project.source == "stubbed" for project in projects) else "ok"
    return DriveScanResponse(status=status, detail=detail, projects=projects)


@router.get("/drive/scan/status")
def drive_scan_status() -> dict[str, str]:
    """Return a stubbed response representing drive scanning state."""

    return {"status": "idle", "detail": "Drive scanning is not available in tests"}
