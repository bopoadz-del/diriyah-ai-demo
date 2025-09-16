"""
Enhanced Google Drive Router for Diriyah Brain AI
Comprehensive file analysis and management
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks, Query
from typing import List, Dict, Any, Optional
import logging
import asyncio
from datetime import datetime
import json

from ..enhanced_drive_client import EnhancedDriveClient
from ..config import get_settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/enhanced-drive", tags=["Enhanced Drive"])

# Global client instance
drive_client = EnhancedDriveClient()
analysis_cache = {}
scan_status = {"status": "idle", "progress": 0, "total": 0, "current_file": ""}

@router.get("/auth")
async def start_auth():
    """Start Google Drive OAuth flow"""
    try:
        settings = get_settings()
        auth_url = drive_client.authenticate(
            client_id=settings.google_client_id,
            client_secret=settings.google_client_secret,
            redirect_uri=settings.google_redirect_uri
        )
        return {"auth_url": auth_url}
    except Exception as e:
        logger.error(f"Auth start error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/callback")
async def auth_callback(code: str):
    """Complete Google Drive OAuth flow"""
    try:
        settings = get_settings()
        drive_client.complete_auth(
            authorization_code=code,
            client_id=settings.google_client_id,
            client_secret=settings.google_client_secret,
            redirect_uri=settings.google_redirect_uri
        )
        return {"status": "success", "message": "Google Drive connected successfully"}
    except Exception as e:
        logger.error(f"Auth callback error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/scan-all")
async def start_comprehensive_scan(background_tasks: BackgroundTasks):
    """Start comprehensive scan of all Google Drive files"""
    try:
        if not drive_client.service:
            raise HTTPException(status_code=401, detail="Google Drive not authenticated")
        
        background_tasks.add_task(perform_comprehensive_scan)
        return {"status": "started", "message": "Comprehensive scan initiated"}
    except Exception as e:
        logger.error(f"Scan start error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

async def perform_comprehensive_scan():
    """Perform comprehensive scan in background"""
    global analysis_cache, scan_status
    
    try:
        scan_status["status"] = "scanning"
        scan_status["progress"] = 0
        scan_status["current_file"] = "Discovering files..."
        
        # Get all files
        all_files = drive_client.scan_all_files(include_shared=True)
        scan_status["total"] = len(all_files)
        
        logger.info(f"Starting analysis of {len(all_files)} files")
        
        # Analyze each file
        for i, file_info in enumerate(all_files):
            try:
                scan_status["current_file"] = file_info.get('name', 'Unknown')
                scan_status["progress"] = i + 1
                
                analysis = drive_client.analyze_file(file_info)
                analysis_cache[file_info['id']] = analysis
                
                # Log progress every 50 files
                if (i + 1) % 50 == 0:
                    logger.info(f"Analyzed {i + 1}/{len(all_files)} files")
                
            except Exception as e:
                logger.error(f"Error analyzing file {file_info.get('name')}: {e}")
                continue
        
        scan_status["status"] = "completed"
        scan_status["current_file"] = "Scan completed"
        logger.info(f"Comprehensive scan completed. Analyzed {len(analysis_cache)} files")
        
    except Exception as e:
        scan_status["status"] = "error"
        scan_status["current_file"] = f"Error: {str(e)}"
        logger.error(f"Comprehensive scan error: {e}")

@router.get("/scan-status")
async def get_scan_status():
    """Get current scan status"""
    return scan_status

@router.get("/files")
async def get_analyzed_files(
    file_type: Optional[str] = Query(None, description="Filter by file type"),
    search: Optional[str] = Query(None, description="Search in content"),
    limit: int = Query(100, description="Limit results")
):
    """Get analyzed files with optional filtering"""
    try:
        if not analysis_cache:
            return {"files": [], "total": 0, "message": "No files analyzed yet. Run scan first."}
        
        files = list(analysis_cache.values())
        
        # Filter by file type
        if file_type:
            files = [f for f in files if file_type.lower() in f.get('metadata', {}).get('file_type', '').lower()]
        
        # Search in content
        if search:
            files = drive_client.search_content(search, files)
        
        # Limit results
        files = files[:limit]
        
        return {
            "files": files,
            "total": len(files),
            "total_analyzed": len(analysis_cache)
        }
        
    except Exception as e:
        logger.error(f"Get files error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/file/{file_id}")
async def get_file_analysis(file_id: str):
    """Get detailed analysis for a specific file"""
    try:
        if file_id not in analysis_cache:
            raise HTTPException(status_code=404, detail="File not found or not analyzed")
        
        return analysis_cache[file_id]
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get file analysis error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/search")
async def search_files(
    query: str = Query(..., description="Search query"),
    limit: int = Query(50, description="Limit results")
):
    """Search through all analyzed files"""
    try:
        if not analysis_cache:
            return {"results": [], "message": "No files analyzed yet. Run scan first."}
        
        files = list(analysis_cache.values())
        results = drive_client.search_content(query, files)
        
        return {
            "results": results[:limit],
            "total_results": len(results),
            "query": query
        }
        
    except Exception as e:
        logger.error(f"Search error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/statistics")
async def get_drive_statistics():
    """Get comprehensive statistics about analyzed files"""
    try:
        if not analysis_cache:
            return {"message": "No files analyzed yet. Run scan first."}
        
        files = list(analysis_cache.values())
        
        # File type statistics
        file_types = {}
        analysis_status = {}
        total_size = 0
        shared_files = 0
        
        for file_data in files:
            # File types
            file_type = file_data.get('metadata', {}).get('file_type', 'Unknown')
            file_types[file_type] = file_types.get(file_type, 0) + 1
            
            # Analysis status
            status = file_data.get('analysis_status', 'unknown')
            analysis_status[status] = analysis_status.get(status, 0) + 1
            
            # Size calculation
            try:
                size = int(file_data.get('size', 0))
                total_size += size
            except:
                pass
            
            # Shared files
            if file_data.get('shared', False):
                shared_files += 1
        
        return {
            "total_files": len(files),
            "file_types": file_types,
            "analysis_status": analysis_status,
            "total_size_bytes": total_size,
            "total_size_mb": round(total_size / (1024 * 1024), 2),
            "shared_files": shared_files,
            "scan_timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Statistics error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/folders")
async def get_folder_structure():
    """Get Google Drive folder structure"""
    try:
        if not drive_client.service:
            raise HTTPException(status_code=401, detail="Google Drive not authenticated")
        
        folder_structure = drive_client.get_folder_structure()
        return {"folders": folder_structure}
        
    except Exception as e:
        logger.error(f"Folder structure error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/archives")
async def get_archive_files():
    """Get all ZIP and RAR archive files with their contents"""
    try:
        if not analysis_cache:
            return {"archives": [], "message": "No files analyzed yet. Run scan first."}
        
        archives = []
        for file_data in analysis_cache.values():
            file_type = file_data.get('metadata', {}).get('file_type', '')
            if 'Archive' in file_type:
                archives.append(file_data)
        
        return {
            "archives": archives,
            "total": len(archives)
        }
        
    except Exception as e:
        logger.error(f"Archives error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/documents")
async def get_document_files():
    """Get all document files (PDF, Word, etc.)"""
    try:
        if not analysis_cache:
            return {"documents": [], "message": "No files analyzed yet. Run scan first."}
        
        documents = []
        document_types = ['PDF Document', 'Word Document', 'Google Document', 'Text File']
        
        for file_data in analysis_cache.values():
            file_type = file_data.get('metadata', {}).get('file_type', '')
            if any(doc_type in file_type for doc_type in document_types):
                documents.append(file_data)
        
        return {
            "documents": documents,
            "total": len(documents)
        }
        
    except Exception as e:
        logger.error(f"Documents error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/spreadsheets")
async def get_spreadsheet_files():
    """Get all spreadsheet files (Excel, Google Sheets, CSV)"""
    try:
        if not analysis_cache:
            return {"spreadsheets": [], "message": "No files analyzed yet. Run scan first."}
        
        spreadsheets = []
        sheet_types = ['Excel Spreadsheet', 'Google Spreadsheet', 'CSV Data']
        
        for file_data in analysis_cache.values():
            file_type = file_data.get('metadata', {}).get('file_type', '')
            if any(sheet_type in file_type for sheet_type in sheet_types):
                spreadsheets.append(file_data)
        
        return {
            "spreadsheets": spreadsheets,
            "total": len(spreadsheets)
        }
        
    except Exception as e:
        logger.error(f"Spreadsheets error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/images")
async def get_image_files():
    """Get all image files"""
    try:
        if not analysis_cache:
            return {"images": [], "message": "No files analyzed yet. Run scan first."}
        
        images = []
        for file_data in analysis_cache.values():
            file_type = file_data.get('metadata', {}).get('file_type', '')
            if 'Image' in file_type:
                images.append(file_data)
        
        return {
            "images": images,
            "total": len(images)
        }
        
    except Exception as e:
        logger.error(f"Images error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/cad-files")
async def get_cad_files():
    """Get all CAD files"""
    try:
        if not analysis_cache:
            return {"cad_files": [], "message": "No files analyzed yet. Run scan first."}
        
        cad_files = []
        for file_data in analysis_cache.values():
            file_type = file_data.get('metadata', {}).get('file_type', '')
            if 'CAD' in file_type:
                cad_files.append(file_data)
        
        return {
            "cad_files": cad_files,
            "total": len(cad_files)
        }
        
    except Exception as e:
        logger.error(f"CAD files error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/reanalyze/{file_id}")
async def reanalyze_file(file_id: str):
    """Reanalyze a specific file"""
    try:
        if not drive_client.service:
            raise HTTPException(status_code=401, detail="Google Drive not authenticated")
        
        # Get file info
        file_info = drive_client.service.files().get(
            fileId=file_id,
            fields="id, name, mimeType, size, createdTime, modifiedTime, parents, shared, owners, permissions, webViewLink"
        ).execute()
        
        # Analyze the file
        analysis = drive_client.analyze_file(file_info)
        analysis_cache[file_id] = analysis
        
        return analysis
        
    except Exception as e:
        logger.error(f"Reanalyze error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/cache")
async def clear_analysis_cache():
    """Clear the analysis cache"""
    global analysis_cache
    analysis_cache.clear()
    return {"status": "success", "message": "Analysis cache cleared"}

@router.get("/export-analysis")
async def export_analysis():
    """Export all analysis data as JSON"""
    try:
        if not analysis_cache:
            return {"message": "No analysis data to export"}
        
        export_data = {
            "export_timestamp": datetime.now().isoformat(),
            "total_files": len(analysis_cache),
            "files": list(analysis_cache.values())
        }
        
        return export_data
        
    except Exception as e:
        logger.error(f"Export error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

