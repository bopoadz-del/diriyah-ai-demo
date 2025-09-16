from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import RedirectResponse
from diriyah_brain_ai.drive_adapter import GoogleDriveAdapter
import logging
import os

router = APIRouter()
logger = logging.getLogger(__name__)
drive_adapter = GoogleDriveAdapter()

@router.get("/drive/files")
async def drive_files(project: str):
    try:
        # In a real scenario, you would get the folder_id from the database based on the project name
        # For this example, we'll use the project name as the folder_id
        files = await drive_adapter.list_files(project.lower())
        return {"files": files}
    except Exception as e:
        logger.error(f"Drive files error: {e}")
        raise HTTPException(status_code=500, detail="Failed to load drive files")

@router.get("/drive/search")
async def drive_search(project: str, q: str):
    try:
        # Similarly, use project name as folder_id for mock
        matches = await drive_adapter.search_files(project.lower(), q)
        return {"matches": matches}
    except Exception as e:
        logger.error(f"Drive search error: {e}")
        raise HTTPException(status_code=500, detail="Failed to search drive files")

@router.get("/drive/callback")
async def drive_callback(request: Request):
    """Handle Google OAuth callback for Drive integration"""
    try:
        # Get the authorization code from the callback
        code = request.query_params.get("code")
        if not code:
            raise HTTPException(status_code=400, detail="Authorization code not provided")
        
        # Exchange code for access token (implement in drive_adapter)
        # This would typically store the token for the user session
        logger.info(f"Received OAuth callback with code: {code[:10]}...")
        
        # Redirect back to the main application
        return RedirectResponse(url="/")
        
    except Exception as e:
        logger.error(f"Drive callback error: {e}")
        raise HTTPException(status_code=500, detail="OAuth callback failed")

@router.get("/drive/auth")
async def drive_auth():
    """Initiate Google Drive OAuth flow"""
    try:
        client_id = os.getenv("GOOGLE_CLIENT_ID")
        redirect_uri = os.getenv("GOOGLE_REDIRECT_URI")
        
        if not client_id or not redirect_uri:
            raise HTTPException(status_code=500, detail="Google OAuth not configured")
        
        # Build OAuth URL
        oauth_url = (
            f"https://accounts.google.com/o/oauth2/auth?"
            f"client_id={client_id}&"
            f"redirect_uri={redirect_uri}&"
            f"scope=https://www.googleapis.com/auth/drive.readonly&"
            f"response_type=code&"
            f"access_type=offline"
        )
        
        return RedirectResponse(url=oauth_url)
        
    except Exception as e:
        logger.error(f"Drive auth error: {e}")
        raise HTTPException(status_code=500, detail="Failed to initiate OAuth flow")


