"""Drive diagnostic endpoints for the demo UI."""
from typing import Any, Dict
from fastapi import APIRouter
from backend.services.google_drive import get_drive_service, list_project_folders

router = APIRouter()

@router.get("/drive/diagnose")
def drive_diagnose() -> Dict[str, Any]:
    """Return debugging details about the Google Drive connection."""
    try:
        service = get_drive_service()
        about = service.about().get(fields="user(emailAddress,displayName)").execute()
        files = list_project_folders()
        breakdown: Dict[str, int] = {}
        for drive_file in files:
            mime_type = drive_file.get("mimeType", "unknown")
            breakdown[mime_type] = breakdown.get(mime_type, 0) + 1
        return {
            "status": "ok",
            "connected_as": about["user"].get("emailAddress"),
            "total_files": len(files),
            "file_type_breakdown": breakdown,
            "sample_files": [drive_file.get("name") for drive_file in files[:10]],
        }
    except Exception as exc:  # pragma: no cover - defensive logging path
        return {"status": "error", "detail": str(exc)}
