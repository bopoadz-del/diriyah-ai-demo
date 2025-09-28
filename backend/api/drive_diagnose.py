from fastapi import APIRouter
from backend.services.google_drive import get_drive_service, list_project_folders
router = APIRouter()
@router.get("/drive/diagnose")
def drive_diagnose():
    try:
        service = get_drive_service()
        about = service.about().get(fields="user(emailAddress,displayName)").execute()
        files = list_project_folders()
        types = {}
        for f in files:
            mt = f.get("mimeType", "unknown")
            types[mt] = types.get(mt, 0) + 1
        return {"status": "ok", "connected_as": about["user"]["emailAddress"], "total_files": len(files), "file_type_breakdown": types, "sample_files": [f["name"] for f in files[:10]]}
    except Exception as e:
        return {"status": "error", "detail": str(e)}
