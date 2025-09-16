from fastapi import APIRouter, HTTPException
import sqlite3
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

@router.get("/projects/list")
async def projects_list():
    try:
        conn = sqlite3.connect("diriyah.db")
        c = conn.cursor()
        c.execute("SELECT id, name FROM projects")
        projects = [{'id': row[0], 'name': row[1]} for row in c.fetchall()]
        conn.close()
        return projects
    except Exception as e:
        logger.error(f"Projects list error: {e}")
        raise HTTPException(status_code=500, detail="Failed to load projects")


