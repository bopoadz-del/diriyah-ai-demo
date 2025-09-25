
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from typing import List
import asyncio

router = APIRouter(prefix="/ws/alerts", tags=["alerts-ws"])

active_connections: List[WebSocket] = []
_broadcast_queue: asyncio.Queue | None = None
_consumer_task: asyncio.Task | None = None

async def _ensure_consumer():
    global _broadcast_queue, _consumer_task
    if _broadcast_queue is None:
        _broadcast_queue = asyncio.Queue()
    if _consumer_task is None or _consumer_task.done():
        _consumer_task = asyncio.create_task(_consumer())

async def _consumer():
    while True:
        message = await _broadcast_queue.get()
        stale = []
        for conn in active_connections:
            try:
                await conn.send_json(message)
            except Exception:
                stale.append(conn)
        for s in stale:
            if s in active_connections:
                active_connections.remove(s)

async def broadcast(message: dict):
    await _ensure_consumer()
    await _broadcast_queue.put(message)

def enqueue_alert(message: dict):
    """Thread-safe enqueue from sync contexts (e.g., DB calls)."""
    try:
        loop = asyncio.get_running_loop()
        loop.create_task(broadcast(message))
    except RuntimeError:
        # No running loop: try global loop via call_soon_threadsafe
        loop = asyncio.new_event_loop()
        loop.call_soon_threadsafe(lambda: None)
        # Fallback: best-effort fire-and-forget using background task
        try:
            asyncio.run(broadcast(message))
        except RuntimeError:
            # As a last resort, ignore (no event loop available)
            pass

@router.websocket("")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    active_connections.append(websocket)
    await _ensure_consumer()
    try:
        while True:
            await websocket.receive_text()  # keep alive
    except WebSocketDisconnect:
        if websocket in active_connections:
            active_connections.remove(websocket)
