"""
teams.py
--------

Stub module for Microsoft Teams meeting minutes integration.  A real
version would access Teams call transcripts and automatically
generate Minutes of Meeting (MoM) with action items and owners.  This
stub returns a static message.

Endpoint:

POST /teams/mom

Returns:
  A placeholder MoM
"""

from fastapi import APIRouter

router = APIRouter()

@router.post("/teams/mom")
async def mom_from_meeting():
    return {
        "status": "stub",
        "minutes": "MoM would be generated from the Teams recording here."
    }