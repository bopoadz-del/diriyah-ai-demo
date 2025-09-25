from fastapi import APIRouter
from backend.services.drive_service import list_files, upload_file
router = APIRouter()
@router.get("/drive/list")
def list_drive_files():
    try: return {"status":"ok","files":list_files()}
    except Exception as e: return {"status":"error","message":str(e)}
@router.post("/drive/upload")
def upload_drive_file(file_path: str):
    try: return {"status":"ok","file_id":upload_file(file_path)}
    except Exception as e: return {"status":"error","message":str(e)}