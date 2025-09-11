"""
powerbi.py
----------

Stub module for Power BI integration.  A complete integration would
embed dashboard summaries or generate reports on demand.  This stub
returns a dummy summary.

Endpoint:

GET /powerbi/summary

Returns:
  A placeholder KPI summary
"""

from fastapi import APIRouter

router = APIRouter()

@router.get("/powerbi/summary")
async def summary():
    return {
        "status": "stub",
        "summary": "KPI summary would be retrieved from Power BI here."
    }