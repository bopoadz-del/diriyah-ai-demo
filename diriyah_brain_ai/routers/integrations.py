from fastapi import APIRouter, Form, HTTPException
import sqlite3
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

# WhatsApp endpoints
@router.post("/whatsapp/register")
async def whatsapp_register(user_id: int = Form(...), project_id: int = Form(...), group_id: str = Form(...)):
    try:
        conn = sqlite3.connect("diriyah.db")
        c = conn.cursor()
        c.execute("INSERT INTO whatsapp_groups (user_id, project_id, group_id) VALUES (?, ?, ?)",
                 (user_id, project_id, group_id))
        conn.commit()
        conn.close()
        return {"status": "success", "message": "WhatsApp group registered"}
    except Exception as e:
        logger.error(f"WhatsApp register error: {e}")
        raise HTTPException(status_code=500, detail="Registration failed")

@router.get("/whatsapp/list")
async def whatsapp_list(user_id: int, project_id: int):
    try:
        conn = sqlite3.connect("diriyah.db")
        c = conn.cursor()
        c.execute("SELECT group_id FROM whatsapp_groups WHERE user_id = ? AND project_id = ?",
                 (user_id, project_id))
        groups = [row[0] for row in c.fetchall()]
        conn.close()
        return {"groups": groups}
    except Exception as e:
        logger.error(f"WhatsApp list error: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch groups")

# Teams endpoints
@router.post("/teams/connect")
async def teams_connect(user_id: int = Form(...), project: str = Form(...), channel_id: str = Form(...)):
    try:
        conn = sqlite3.connect("diriyah.db")
        c = conn.cursor()
        c.execute("INSERT INTO teams_connections (user_id, project, channel_id) VALUES (?, ?, ?)",
                 (user_id, project, channel_id))
        conn.commit()
        conn.close()
        return {"status": "connected", "message": "Teams channel connected"}
    except Exception as e:
        logger.error(f"Teams connect error: {e}")
        raise HTTPException(status_code=500, detail="Connection failed")

@router.get("/teams/status")
async def teams_status(user_id: int):
    try:
        conn = sqlite3.connect("diriyah.db")
        c = conn.cursor()
        c.execute("SELECT project, channel_id FROM teams_connections WHERE user_id = ?", (user_id,))
        result = c.fetchone()
        conn.close()
        
        if result:
            return {"status": "connected", "project": result[0], "channel_id": result[1]}
        return {"status": "not connected"}
    except Exception as e:
        logger.error(f"Teams status error: {e}")
        raise HTTPException(status_code=500, detail="Failed to get status")


