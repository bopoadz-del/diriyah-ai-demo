"""
aconex.py
---------

Stub module for Aconex correspondence integration.  In a production
system this would fetch RFIs, NCRs, Submittals and other project
correspondence from Aconex via their API.  Here we return a static
example list.

Endpoint:

GET /aconex/correspondence

Returns:
  A placeholder correspondence list
"""

from fastapi import APIRouter

router = APIRouter()

@router.get("/aconex/correspondence")
async def correspondence():
    return {
        "status": "stub",
        "correspondence": ["RFI‑1025", "NCR‑45", "VO‑11"]
    }