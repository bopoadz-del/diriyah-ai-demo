"""
p6.py
------

Stub module for Primavera P6 integration.  In a full implementation
this would query the P6 API or database for milestone completion
percentages, planned versus actual dates and critical path status.  It
returns a placeholder response here.

Endpoint:

GET /p6/milestones

Returns:
  A list of fake milestone statuses
"""

from fastapi import APIRouter

router = APIRouter()

@router.get("/p6/milestones")
async def milestones():
    # Example milestones; replace with live P6 data
    return {
        "status": "stub",
        "milestones": [
            {"name": "Boulevard NW finish", "status": "Delayed"},
            {"name": "Northern Community utilities", "status": "On schedule"}
        ]
    }