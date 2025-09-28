from fastapi import APIRouter, Form
router = APIRouter()
@router.post("/project/intel")
def project_intel(project: str = Form("default")):
    return {"project": project, "timeline_risk": 35, "budget_forecast": 82, "resource_efficiency": 68, "quality_risk": 22}
