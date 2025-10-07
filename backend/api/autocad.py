"""AutoCAD take-off endpoints backed by Google Drive downloads."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from backend.services.cad_takeoff import CADTakeoffService

router = APIRouter()
_service = CADTakeoffService()


@router.get("/autocad/takeoff")
def autocad_takeoff(file_id: str = Query(..., description="Google Drive file identifier")) -> dict[str, object]:
    """Run a lightweight AutoCAD take-off over the Drive-backed DWG."""

    if not file_id.strip():
        raise HTTPException(status_code=400, detail="file_id is required")

    result = _service.process_dwg(file_id)
    return {"status": result.get("status", "ok"), "result": result}


__all__ = ["router"]
