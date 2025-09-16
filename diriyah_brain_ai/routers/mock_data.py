from fastapi import APIRouter

router = APIRouter()

@router.get("/drive/files")
async def drive_files(project: str):
    # Mock file data
    files = [
        {"name": "Project Plan.pdf", "url": "#", "size": "2.4MB", "modified": "2023-11-15"},
        {"name": "Budget Report.xlsx", "url": "#", "size": "1.2MB", "modified": "2023-11-14"},
        {"name": "Design Specifications.docx", "url": "#", "size": "3.1MB", "modified": "2023-11-13"}
    ]
    return {"files": files}

@router.get("/drive/search")
async def drive_search(project: str, q: str):
    # Mock search results
    results = [
        {"name": f"{q} Analysis Report.pdf", "url": "#", "relevance": "95%"},
        {"name": f"Meeting Notes about {q}.docx", "url": "#", "relevance": "88%"},
        {"name": f"{q} Budget Allocation.xlsx", "url": "#", "relevance": "92%"}
    ]
    return {"matches": results}

@router.get("/aconex/recent")
async def aconex_recent(project: str):
    # Mock Aconex data
    correspondence = [
        {"from": "Contractor", "subject": "RFI Response", "date": "2023-11-15", "status": "Reviewed"},
        {"from": "Client", "subject": "Design Approval", "date": "2023-11-14", "status": "Pending"},
        {"from": "Architect", "subject": "Revision Request", "date": "2023-11-13", "status": "Completed"}
    ]
    return {"correspondence": correspondence}

@router.get("/p6/milestones")
async def p6_milestones(project: str):
    # Mock P6 data
    milestones = [
        {"name": "Foundation Complete", "date": "2023-12-01", "status": "On Track", "progress": "85%"},
        {"name": "Design Approval", "date": "2023-11-20", "status": "Completed", "progress": "100%"},
        {"name": "Structural Steel", "date": "2024-01-15", "status": "Planning", "progress": "30%"}
    ]
    return {"milestones": milestones}

@router.get("/powerbi/summary")
async def powerbi_summary(project: str):
    # Mock PowerBI data
    summary = {
        "budget": {"spent": "75%", "remaining": "25%", "variance": "+2%"},
        "schedule": {"completed": "80%", "behind": "5 days", "critical_path": "On track"},
        "resources": {"utilization": "78%", "shortages": "2 positions", "overtime": "12%"},
        "risks": {"high": 3, "medium": 8, "low": 15}
    }
    return {"summary": summary}


