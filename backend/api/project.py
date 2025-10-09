from fastapi import APIRouter, Body, Form

router = APIRouter()

try:  # pragma: no cover - optional multipart dependency
    import multipart  # type: ignore
except ModuleNotFoundError:  # pragma: no cover - handled gracefully
    multipart = None  # type: ignore[assignment]

_project_param = Form("default") if multipart is not None else Body("default")


@router.post("/project/intel")
def project_intel(project: str = _project_param):
    return {
        "project": project,
        "timeline_risk": 35,
        "budget_forecast": 82,
        "resource_efficiency": 68,
        "quality_risk": 22,
    }
