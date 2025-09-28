from fastapi import APIRouter, UploadFile, File
from backend.services.google_drive import upload_to_drive
from backend.services.boq_parser import BOQParserService
from backend.services.cad_takeoff import CADTakeoffService
router = APIRouter()
@router.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    file_id = upload_to_drive(file)
    if file.filename.lower().endswith((".xlsx", ".xls")):
        result = BOQParserService().parse_excel(file_id)
    elif file.filename.lower().endswith(".dwg"):
        result = CADTakeoffService().process_dwg(file_id)
    else:
        result = {"message": "File stored in Drive", "file_id": file_id}
    return {"file_id": file_id, "result": result}
