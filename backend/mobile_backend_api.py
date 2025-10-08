"""FastAPI backend tailored for the Diriyah mobile application.

The module intentionally lives next to the primary ``backend.main`` app so it
can share the same deployment pipeline on Render.  The API surface is largely
driven by the mobile clients and therefore implements its own database models
and routes that are isolated from the rest of the codebase.

Key characteristics of this implementation:

* Works out-of-the-box on Render by relying on ``DATABASE_URL`` and the
  standard ``PORT`` variables.  When Render injects the PostgreSQL connection
  string we automatically create the required tables if they do not exist.
* Falls back to sensible local defaults which makes ad‑hoc debugging easier –
  for example when a developer runs ``uvicorn backend.mobile_backend_api:app``
  on their laptop without provisioning PostgreSQL or S3 credentials.
* Optional integrations (OpenAI Whisper, Amazon S3, etc.) are imported lazily
  and failures are logged instead of crashing the service.  This mirrors how
  the production deployment can temporarily miss credentials when debugging a
  Render instance.

The implementation is a modernised version of the specification shared by the
product team.  Besides aligning imports with the project's existing
dependencies, the only adjustments are:

* more defensive error handling around optional services
* stricter logging configuration for better observability on Render
* use of ``sqlalchemy.orm.declarative_base`` to avoid SQLAlchemy 2.0 warnings
* respect of the ``PORT`` environment variable when running as ``__main__``
"""

from __future__ import annotations

import logging
import os
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

import aiofiles
from fastapi import (
    Depends,
    FastAPI,
    File,
    Form,
    HTTPException,
    UploadFile,
    WebSocket,
    WebSocketDisconnect,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from openai import OpenAI
from passlib.context import CryptContext
from pydantic import BaseModel, EmailStr
from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    Float,
    Integer,
    String,
    Text,
    create_engine,
)
from sqlalchemy.orm import declarative_base, sessionmaker

try:  # Optional dependencies that might not be present during local debugging
    import boto3
except Exception:  # pragma: no cover - only happens when boto3 is missing
    boto3 = None  # type: ignore

try:
    import jwt
except Exception:  # pragma: no cover - only happens when PyJWT is missing
    jwt = None  # type: ignore


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

logger = logging.getLogger("mobile-backend")

SECRET_KEY = os.getenv("SECRET_KEY", "change-this-secret")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "sqlite:///" + str(Path("./diriyah_mobile.db").resolve()),
)

UPLOAD_DIR = Path(os.getenv("UPLOAD_DIR", "./uploads"))
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

AWS_ACCESS_KEY = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
S3_BUCKET = os.getenv("S3_BUCKET", "diriyah-mobile-uploads")
S3_REGION = os.getenv("S3_REGION", "me-south-1")

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")


# ---------------------------------------------------------------------------
# Database models
# ---------------------------------------------------------------------------

Base = declarative_base()
engine = create_engine(DATABASE_URL, pool_pre_ping=True, future=True)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    email = Column(String, unique=True, index=True)
    name = Column(String)
    hashed_password = Column(String)
    role = Column(String, default="user")
    created_at = Column(DateTime, default=datetime.utcnow)
    last_login = Column(DateTime)
    fcm_token = Column(String, nullable=True)


class Project(Base):
    __tablename__ = "projects"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String)
    description = Column(Text)
    status = Column(String, default="active")
    progress = Column(Float, default=0.0)
    user_id = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    metadata = Column(JSON)


class Alert(Base):
    __tablename__ = "alerts"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String)
    project_id = Column(String, nullable=True)
    title = Column(String)
    message = Column(Text)
    severity = Column(String, default="medium")
    read = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    metadata = Column(JSON)


class Task(Base):
    __tablename__ = "tasks"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String)
    project_id = Column(String)
    title = Column(String)
    description = Column(Text)
    priority = Column(String, default="medium")
    status = Column(String, default="pending")
    completed = Column(Boolean, default=False)
    due_date = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String)
    role = Column(String)
    content = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    metadata = Column(JSON)


class UploadedFile(Base):
    __tablename__ = "uploaded_files"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String)
    project_id = Column(String, nullable=True)
    filename = Column(String)
    file_type = Column(String)
    file_size = Column(Integer)
    s3_url = Column(String, nullable=True)
    local_path = Column(String, nullable=True)
    description = Column(Text, nullable=True)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    metadata = Column(JSON)


Base.metadata.create_all(bind=engine)


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserCreate(BaseModel):
    email: EmailStr
    name: str
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str
    user: Dict[str, Any]


class ChatMessageCreate(BaseModel):
    message: str
    project_id: Optional[str] = None


class ProjectCreate(BaseModel):
    name: str
    description: str
    metadata: Optional[Dict[str, Any]] = None


class TaskCreate(BaseModel):
    project_id: str
    title: str
    description: str
    priority: str = "medium"
    due_date: Optional[datetime] = None


class FCMTokenUpdate(BaseModel):
    fcm_token: str


# ---------------------------------------------------------------------------
# FastAPI app configuration
# ---------------------------------------------------------------------------


app = FastAPI(
    title="Diriyah Brain AI - Mobile Backend",
    description="Mobile specific backend API for Diriyah Brain AI",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer()

openai_client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None
s3_client = (
    boto3.client(
        "s3",
        aws_access_key_id=AWS_ACCESS_KEY,
        aws_secret_access_key=AWS_SECRET_KEY,
        region_name=S3_REGION,
    )
    if boto3 and AWS_ACCESS_KEY and AWS_SECRET_KEY
    else None
)


class ConnectionManager:
    def __init__(self) -> None:
        self.active_connections: Dict[str, WebSocket] = {}

    async def connect(self, user_id: str, websocket: WebSocket) -> None:
        await websocket.accept()
        self.active_connections[user_id] = websocket
        logger.info("User %s connected via WebSocket", user_id)

    def disconnect(self, user_id: str) -> None:
        if user_id in self.active_connections:
            del self.active_connections[user_id]
            logger.info("User %s disconnected", user_id)

    async def send_personal_message(self, user_id: str, message: dict) -> None:
        websocket = self.active_connections.get(user_id)
        if websocket is None:
            return
        try:
            await websocket.send_json(message)
        except Exception as exc:  # pragma: no cover - network exceptions
            logger.error("Error sending message to %s: %s", user_id, exc)
            self.disconnect(user_id)

    async def broadcast(self, message: dict) -> None:
        disconnected: List[str] = []
        for user_id, websocket in self.active_connections.items():
            try:
                await websocket.send_json(message)
            except Exception:  # pragma: no cover - network exceptions
                disconnected.append(user_id)
        for user_id in disconnected:
            self.disconnect(user_id)


manager = ConnectionManager()


# ---------------------------------------------------------------------------
# Helper utilities
# ---------------------------------------------------------------------------


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def _jwt_module() -> Any:
    if jwt is None:
        raise HTTPException(status_code=500, detail="JWT support not installed")
    return jwt


def create_access_token(data: dict) -> str:
    module = _jwt_module()
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return module.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str) -> dict:
    module = _jwt_module()
    try:
        return module.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except module.ExpiredSignatureError as exc:  # type: ignore[attr-defined]
        raise HTTPException(status_code=401, detail="Token has expired") from exc
    except module.PyJWTError as exc:  # type: ignore[attr-defined]
        raise HTTPException(status_code=401, detail="Invalid token") from exc


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db=Depends(get_db),
):
    token = credentials.credentials
    payload = decode_token(token)
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token")
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


async def upload_to_s3(file_content: bytes, filename: str, content_type: str) -> Optional[str]:
    if not s3_client:
        return None
    try:
        key = f"mobile-uploads/{datetime.now().strftime('%Y/%m/%d')}/{filename}"
        s3_client.put_object(
            Bucket=S3_BUCKET,
            Key=key,
            Body=file_content,
            ContentType=content_type,
        )
        return f"https://{S3_BUCKET}.s3.{S3_REGION}.amazonaws.com/{key}"
    except Exception as exc:  # pragma: no cover - depends on AWS credentials
        logger.error("S3 upload error: %s", exc)
        return None


async def process_audio_to_text(audio_file: bytes) -> str:
    if not openai_client:
        return "Audio transcription not available"
    temp_file = UPLOAD_DIR / f"temp_{uuid.uuid4()}.mp3"
    try:
        async with aiofiles.open(temp_file, "wb") as file_handle:
            await file_handle.write(audio_file)
        with temp_file.open("rb") as audio_stream:
            transcript = openai_client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_stream,
            )
        return transcript.text
    except Exception as exc:  # pragma: no cover - depends on OpenAI credentials
        logger.error("Audio transcription error: %s", exc)
        return "Error transcribing audio"
    finally:
        if temp_file.exists():
            temp_file.unlink()


async def get_ai_response(message: str, user_id: str, db) -> str:
    if not openai_client:
        return "AI service not available"
    try:
        recent_messages = (
            db.query(ChatMessage)
            .filter(ChatMessage.user_id == user_id)
            .order_by(ChatMessage.created_at.desc())
            .limit(10)
            .all()
        )
        messages = [
            {
                "role": "system",
                "content": (
                    "You are Diriyah Brain AI, an intelligent assistant for "
                    "construction project management."
                ),
            }
        ]
        for msg in reversed(recent_messages):
            messages.append({"role": msg.role, "content": msg.content})
        messages.append({"role": "user", "content": message})
        response = openai_client.chat.completions.create(
            model="gpt-4",
            messages=messages,
            temperature=0.7,
            max_tokens=500,
        )
        return response.choices[0].message.content
    except Exception as exc:  # pragma: no cover - depends on OpenAI credentials
        logger.error("AI response error: %s", exc)
        return "Sorry, I encountered an error processing your request."


async def send_push_notification(user_id: str, title: str, body: str, db) -> None:
    user = db.query(User).filter(User.id == user_id).first()
    if user and user.fcm_token:
        logger.info("Push notification to %s: %s", user_id, title)


# ---------------------------------------------------------------------------
# Authentication endpoints
# ---------------------------------------------------------------------------


@app.post("/api/auth/register", response_model=Token)
async def register(user_data: UserCreate, db=Depends(get_db)):
    existing_user = db.query(User).filter(User.email == user_data.email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    user = User(
        email=user_data.email,
        name=user_data.name,
        hashed_password=get_password_hash(user_data.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    token = create_access_token({"sub": user.id})
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "email": user.email,
            "name": user.name,
            "role": user.role,
        },
    }


@app.post("/api/auth/login", response_model=Token)
async def login(credentials: UserLogin, db=Depends(get_db)):
    user = db.query(User).filter(User.email == credentials.email).first()
    if not user or not verify_password(credentials.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    user.last_login = datetime.utcnow()
    db.commit()
    token = create_access_token({"sub": user.id})
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "email": user.email,
            "name": user.name,
            "role": user.role,
            "token": token,
        },
    }


@app.post("/api/auth/fcm-token")
async def update_fcm_token(
    token_data: FCMTokenUpdate,
    current_user: User = Depends(get_current_user),
    db=Depends(get_db),
):
    current_user.fcm_token = token_data.fcm_token
    db.commit()
    return {"message": "FCM token updated successfully"}


@app.get("/api/auth/me")
async def get_me(current_user: User = Depends(get_current_user)):
    return {
        "id": current_user.id,
        "email": current_user.email,
        "name": current_user.name,
        "role": current_user.role,
    }


# ---------------------------------------------------------------------------
# Websocket endpoint
# ---------------------------------------------------------------------------


@app.websocket("/ws/mobile")
async def websocket_endpoint(websocket: WebSocket, user_id: str, db=Depends(get_db)):
    await manager.connect(user_id, websocket)
    try:
        while True:
            data = await websocket.receive_json()
            message_type = data.get("type")
            if message_type == "chat_message":
                payload = data.get("payload", {})
                user_message = payload.get("message", "")
                chat_msg = ChatMessage(user_id=user_id, role="user", content=user_message)
                db.add(chat_msg)
                db.commit()
                ai_response = await get_ai_response(user_message, user_id, db)
                ai_msg = ChatMessage(user_id=user_id, role="assistant", content=ai_response)
                db.add(ai_msg)
                db.commit()
                await manager.send_personal_message(
                    user_id,
                    {
                        "type": "chat_response",
                        "payload": {
                            "message": ai_response,
                            "timestamp": datetime.utcnow().isoformat(),
                        },
                    },
                )
            elif message_type == "ping":
                await manager.send_personal_message(
                    user_id,
                    {
                        "type": "pong",
                        "payload": {"timestamp": datetime.utcnow().isoformat()},
                    },
                )
    except WebSocketDisconnect:
        manager.disconnect(user_id)
    except Exception as exc:  # pragma: no cover - network exceptions
        logger.error("WebSocket error for user %s: %s", user_id, exc)
        manager.disconnect(user_id)


# ---------------------------------------------------------------------------
# Project endpoints
# ---------------------------------------------------------------------------


@app.get("/api/projects")
async def get_projects(current_user: User = Depends(get_current_user), db=Depends(get_db)):
    projects = db.query(Project).filter(Project.user_id == current_user.id).all()
    return {
        "projects": [
            {
                "id": project.id,
                "name": project.name,
                "description": project.description,
                "status": project.status,
                "progress": project.progress,
                "created_at": project.created_at.isoformat(),
                "updated_at": project.updated_at.isoformat(),
                "metadata": project.metadata or {},
            }
            for project in projects
        ]
    }


@app.post("/api/projects")
async def create_project(
    project_data: ProjectCreate,
    current_user: User = Depends(get_current_user),
    db=Depends(get_db),
):
    project = Project(
        name=project_data.name,
        description=project_data.description,
        user_id=current_user.id,
        metadata=project_data.metadata,
    )
    db.add(project)
    db.commit()
    db.refresh(project)
    return {
        "id": project.id,
        "name": project.name,
        "description": project.description,
        "status": project.status,
        "progress": project.progress,
    }


@app.get("/api/projects/{project_id}")
async def get_project(
    project_id: str,
    current_user: User = Depends(get_current_user),
    db=Depends(get_db),
):
    project = (
        db.query(Project)
        .filter(Project.id == project_id, Project.user_id == current_user.id)
        .first()
    )
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return {
        "id": project.id,
        "name": project.name,
        "description": project.description,
        "status": project.status,
        "progress": project.progress,
        "created_at": project.created_at.isoformat(),
        "updated_at": project.updated_at.isoformat(),
        "metadata": project.metadata or {},
    }


# ---------------------------------------------------------------------------
# Alert endpoints
# ---------------------------------------------------------------------------


@app.get("/api/alerts")
async def get_alerts(current_user: User = Depends(get_current_user), db=Depends(get_db)):
    alerts = (
        db.query(Alert)
        .filter(Alert.user_id == current_user.id)
        .order_by(Alert.created_at.desc())
        .all()
    )
    return {
        "alerts": [
            {
                "id": alert.id,
                "title": alert.title,
                "message": alert.message,
                "severity": alert.severity,
                "read": alert.read,
                "timestamp": alert.created_at.isoformat(),
                "project_id": alert.project_id,
                "metadata": alert.metadata or {},
            }
            for alert in alerts
        ]
    }


@app.post("/api/alerts/{alert_id}/mark-read")
async def mark_alert_read(
    alert_id: str,
    current_user: User = Depends(get_current_user),
    db=Depends(get_db),
):
    alert = (
        db.query(Alert)
        .filter(Alert.id == alert_id, Alert.user_id == current_user.id)
        .first()
    )
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    alert.read = True
    db.commit()
    return {"message": "Alert marked as read"}


# ---------------------------------------------------------------------------
# Task endpoints
# ---------------------------------------------------------------------------


@app.get("/api/tasks")
async def get_tasks(current_user: User = Depends(get_current_user), db=Depends(get_db)):
    tasks = db.query(Task).filter(Task.user_id == current_user.id).all()
    return {
        "tasks": [
            {
                "id": task.id,
                "title": task.title,
                "description": task.description,
                "priority": task.priority,
                "status": task.status,
                "completed": task.completed,
                "due_date": task.due_date.isoformat() if task.due_date else None,
                "project_id": task.project_id,
                "created_at": task.created_at.isoformat(),
            }
            for task in tasks
        ]
    }


@app.post("/api/tasks")
async def create_task(
    task_data: TaskCreate,
    current_user: User = Depends(get_current_user),
    db=Depends(get_db),
):
    task = Task(
        user_id=current_user.id,
        project_id=task_data.project_id,
        title=task_data.title,
        description=task_data.description,
        priority=task_data.priority,
        due_date=task_data.due_date,
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    return {
        "id": task.id,
        "title": task.title,
        "description": task.description,
        "priority": task.priority,
        "due_date": task.due_date.isoformat() if task.due_date else None,
    }


@app.patch("/api/tasks/{task_id}/complete")
async def complete_task(
    task_id: str,
    current_user: User = Depends(get_current_user),
    db=Depends(get_db),
):
    task = (
        db.query(Task)
        .filter(Task.id == task_id, Task.user_id == current_user.id)
        .first()
    )
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    task.completed = True
    task.status = "completed"
    db.commit()
    return {"message": "Task completed"}


# ---------------------------------------------------------------------------
# Chat endpoints
# ---------------------------------------------------------------------------


@app.get("/api/chat/history")
async def get_chat_history(
    current_user: User = Depends(get_current_user),
    db=Depends(get_db),
    limit: int = 50,
):
    messages = (
        db.query(ChatMessage)
        .filter(ChatMessage.user_id == current_user.id)
        .order_by(ChatMessage.created_at.desc())
        .limit(limit)
        .all()
    )
    return {
        "messages": [
            {
                "id": message.id,
                "role": message.role,
                "content": message.content,
                "timestamp": message.created_at.isoformat(),
            }
            for message in reversed(messages)
        ]
    }


@app.post("/api/chat/message")
async def send_chat_message(
    message_data: ChatMessageCreate,
    current_user: User = Depends(get_current_user),
    db=Depends(get_db),
):
    user_msg = ChatMessage(user_id=current_user.id, role="user", content=message_data.message)
    db.add(user_msg)
    db.commit()
    ai_response = await get_ai_response(message_data.message, current_user.id, db)
    ai_msg = ChatMessage(user_id=current_user.id, role="assistant", content=ai_response)
    db.add(ai_msg)
    db.commit()
    return {
        "user_message": {
            "id": user_msg.id,
            "content": user_msg.content,
            "timestamp": user_msg.created_at.isoformat(),
        },
        "ai_response": {
            "id": ai_msg.id,
            "content": ai_msg.content,
            "timestamp": ai_msg.created_at.isoformat(),
        },
    }


# ---------------------------------------------------------------------------
# File upload endpoints
# ---------------------------------------------------------------------------


@app.post("/api/photos/upload")
async def upload_photo(
    photo: UploadFile = File(...),
    description: str = Form(None),
    latitude: float = Form(None),
    longitude: float = Form(None),
    project_id: str = Form(None),
    current_user: User = Depends(get_current_user),
    db=Depends(get_db),
):
    try:
        file_content = await photo.read()
        file_size = len(file_content)
        file_ext = Path(photo.filename).suffix
        unique_filename = f"{uuid.uuid4()}{file_ext}"
        s3_url = await upload_to_s3(file_content, unique_filename, photo.content_type)
        local_path = None
        if not s3_url:
            local_file_path = UPLOAD_DIR / unique_filename
            async with aiofiles.open(local_file_path, "wb") as file_handle:
                await file_handle.write(file_content)
            local_path = str(local_file_path)
        uploaded_file = UploadedFile(
            user_id=current_user.id,
            project_id=project_id,
            filename=unique_filename,
            file_type="photo",
            file_size=file_size,
            s3_url=s3_url,
            local_path=local_path,
            description=description,
            latitude=latitude,
            longitude=longitude,
            metadata={
                "original_filename": photo.filename,
                "content_type": photo.content_type,
            },
        )
        db.add(uploaded_file)
        db.commit()
        db.refresh(uploaded_file)
        logger.info("Photo uploaded: %s by user %s", unique_filename, current_user.id)
        return {
            "id": uploaded_file.id,
            "filename": unique_filename,
            "url": s3_url or f"/api/files/{uploaded_file.id}",
            "message": "Photo uploaded successfully",
        }
    except Exception as exc:  # pragma: no cover - depends on file system
        logger.error("Photo upload error: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to upload photo") from exc


@app.post("/api/files/upload")
async def upload_file(
    file: UploadFile = File(...),
    description: str = Form(None),
    project_id: str = Form(None),
    current_user: User = Depends(get_current_user),
    db=Depends(get_db),
):
    try:
        file_content = await file.read()
        file_size = len(file_content)
        file_ext = Path(file.filename).suffix
        unique_filename = f"{uuid.uuid4()}{file_ext}"
        if file.content_type and file.content_type.startswith("image/"):
            file_type = "image"
        elif file.content_type and file.content_type.startswith("video/"):
            file_type = "video"
        elif file.content_type and file.content_type.startswith("audio/"):
            file_type = "audio"
        else:
            file_type = "document"
        s3_url = await upload_to_s3(file_content, unique_filename, file.content_type)
        local_path = None
        if not s3_url:
            local_file_path = UPLOAD_DIR / unique_filename
            async with aiofiles.open(local_file_path, "wb") as file_handle:
                await file_handle.write(file_content)
            local_path = str(local_file_path)
        uploaded_file = UploadedFile(
            user_id=current_user.id,
            project_id=project_id,
            filename=unique_filename,
            file_type=file_type,
            file_size=file_size,
            s3_url=s3_url,
            local_path=local_path,
            description=description,
            metadata={
                "original_filename": file.filename,
                "content_type": file.content_type,
            },
        )
        db.add(uploaded_file)
        db.commit()
        db.refresh(uploaded_file)
        return {
            "id": uploaded_file.id,
            "filename": unique_filename,
            "file_type": file_type,
            "url": s3_url or f"/api/files/{uploaded_file.id}",
            "message": "File uploaded successfully",
        }
    except Exception as exc:  # pragma: no cover - depends on file system
        logger.error("File upload error: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to upload file") from exc


@app.get("/api/files/{file_id}")
async def get_file(
    file_id: str,
    current_user: User = Depends(get_current_user),
    db=Depends(get_db),
):
    uploaded_file = (
        db.query(UploadedFile)
        .filter(UploadedFile.id == file_id, UploadedFile.user_id == current_user.id)
        .first()
    )
    if not uploaded_file:
        raise HTTPException(status_code=404, detail="File not found")
    if uploaded_file.s3_url:
        return JSONResponse({"url": uploaded_file.s3_url})
    if uploaded_file.local_path and Path(uploaded_file.local_path).exists():
        return FileResponse(uploaded_file.local_path)
    raise HTTPException(status_code=404, detail="File not available")


# ---------------------------------------------------------------------------
# Voice endpoints
# ---------------------------------------------------------------------------


@app.post("/api/voice/upload")
async def upload_voice_message(
    audio: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db=Depends(get_db),
):
    try:
        audio_content = await audio.read()
        transcription = await process_audio_to_text(audio_content)
        chat_msg = ChatMessage(
            user_id=current_user.id,
            role="user",
            content=transcription,
            metadata={"type": "voice", "original_filename": audio.filename},
        )
        db.add(chat_msg)
        db.commit()
        ai_response = await get_ai_response(transcription, current_user.id, db)
        ai_msg = ChatMessage(user_id=current_user.id, role="assistant", content=ai_response)
        db.add(ai_msg)
        db.commit()
        return {
            "transcription": transcription,
            "ai_response": ai_response,
            "message": "Voice message processed successfully",
        }
    except Exception as exc:  # pragma: no cover - depends on OpenAI credentials
        logger.error("Voice upload error: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to process voice message") from exc


@app.post("/api/voice/transcribe")
async def transcribe_audio(audio: UploadFile = File(...), current_user: User = Depends(get_current_user)):
    try:
        audio_content = await audio.read()
        transcription = await process_audio_to_text(audio_content)
        return {"transcription": transcription, "message": "Audio transcribed successfully"}
    except Exception as exc:  # pragma: no cover - depends on OpenAI credentials
        logger.error("Transcription error: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to transcribe audio") from exc


# ---------------------------------------------------------------------------
# Sync endpoints
# ---------------------------------------------------------------------------


@app.post("/api/sync/offline-actions")
async def sync_offline_actions(
    actions: List[Dict[str, Any]],
    current_user: User = Depends(get_current_user),
    db=Depends(get_db),
):
    results = {"processed": 0, "failed": 0, "errors": []}
    for action in actions:
        try:
            action_type = action.get("type")
            if action_type == "create_task":
                task = Task(user_id=current_user.id, **action.get("data", {}))
                db.add(task)
            elif action_type == "update_task":
                task_id = action.get("task_id")
                task = db.query(Task).filter(Task.id == task_id).first()
                if task:
                    for key, value in action.get("data", {}).items():
                        setattr(task, key, value)
            results["processed"] += 1
        except Exception as exc:  # pragma: no cover - depends on payload
            results["failed"] += 1
            results["errors"].append(str(exc))
    db.commit()
    return results


# ---------------------------------------------------------------------------
# Analytics endpoints
# ---------------------------------------------------------------------------


@app.get("/api/analytics/dashboard")
async def get_dashboard_analytics(current_user: User = Depends(get_current_user), db=Depends(get_db)):
    total_projects = db.query(Project).filter(Project.user_id == current_user.id).count()
    active_projects = (
        db.query(Project)
        .filter(Project.user_id == current_user.id, Project.status == "active")
        .count()
    )
    total_tasks = db.query(Task).filter(Task.user_id == current_user.id).count()
    completed_tasks = (
        db.query(Task)
        .filter(Task.user_id == current_user.id, Task.completed.is_(True))
        .count()
    )
    total_alerts = db.query(Alert).filter(Alert.user_id == current_user.id).count()
    unread_alerts = (
        db.query(Alert)
        .filter(Alert.user_id == current_user.id, Alert.read.is_(False))
        .count()
    )
    total_files = db.query(UploadedFile).filter(UploadedFile.user_id == current_user.id).count()
    recent_projects = (
        db.query(Project)
        .filter(Project.user_id == current_user.id)
        .order_by(Project.updated_at.desc())
        .limit(5)
        .all()
    )
    recent_tasks = (
        db.query(Task)
        .filter(Task.user_id == current_user.id)
        .order_by(Task.created_at.desc())
        .limit(5)
        .all()
    )
    completion_rate = (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0
    return {
        "summary": {
            "total_projects": total_projects,
            "active_projects": active_projects,
            "total_tasks": total_tasks,
            "completed_tasks": completed_tasks,
            "completion_rate": round(completion_rate, 1),
            "total_alerts": total_alerts,
            "unread_alerts": unread_alerts,
            "total_files": total_files,
        },
        "recent_projects": [
            {
                "id": project.id,
                "name": project.name,
                "status": project.status,
                "progress": project.progress,
                "updated_at": project.updated_at.isoformat(),
            }
            for project in recent_projects
        ],
        "recent_tasks": [
            {
                "id": task.id,
                "title": task.title,
                "priority": task.priority,
                "completed": task.completed,
                "created_at": task.created_at.isoformat(),
            }
            for task in recent_tasks
        ],
    }


@app.get("/api/analytics/projects/{project_id}")
async def get_project_analytics(
    project_id: str,
    current_user: User = Depends(get_current_user),
    db=Depends(get_db),
):
    project = (
        db.query(Project)
        .filter(Project.id == project_id, Project.user_id == current_user.id)
        .first()
    )
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    tasks = db.query(Task).filter(Task.project_id == project_id).all()
    total_tasks = len(tasks)
    completed_tasks = sum(1 for task in tasks if task.completed)
    alerts = db.query(Alert).filter(Alert.project_id == project_id).all()
    critical_alerts = sum(1 for alert in alerts if alert.severity == "critical")
    files = db.query(UploadedFile).filter(UploadedFile.project_id == project_id).all()
    total_file_size = sum(file.file_size for file in files)
    priority_breakdown = {
        "high": sum(1 for task in tasks if task.priority == "high"),
        "medium": sum(1 for task in tasks if task.priority == "medium"),
        "low": sum(1 for task in tasks if task.priority == "low"),
    }
    status_breakdown = {
        "pending": sum(1 for task in tasks if task.status == "pending"),
        "in_progress": sum(1 for task in tasks if task.status == "in_progress"),
        "completed": sum(1 for task in tasks if task.status == "completed"),
    }
    return {
        "project": {
            "id": project.id,
            "name": project.name,
            "status": project.status,
            "progress": project.progress,
            "created_at": project.created_at.isoformat(),
        },
        "tasks": {
            "total": total_tasks,
            "completed": completed_tasks,
            "completion_rate": round((completed_tasks / total_tasks * 100) if total_tasks else 0, 1),
            "by_priority": priority_breakdown,
            "by_status": status_breakdown,
        },
        "alerts": {"total": len(alerts), "critical": critical_alerts},
        "files": {
            "total": len(files),
            "total_size_mb": round(total_file_size / (1024 * 1024), 2),
        },
    }


@app.get("/api/analytics/activity")
async def get_activity_analytics(
    current_user: User = Depends(get_current_user),
    db=Depends(get_db),
    days: int = 30,
):
    start_date = datetime.utcnow() - timedelta(days=days)
    tasks = (
        db.query(Task)
        .filter(Task.user_id == current_user.id, Task.created_at >= start_date)
        .all()
    )
    files = (
        db.query(UploadedFile)
        .filter(UploadedFile.user_id == current_user.id, UploadedFile.created_at >= start_date)
        .all()
    )
    messages = (
        db.query(ChatMessage)
        .filter(ChatMessage.user_id == current_user.id, ChatMessage.created_at >= start_date)
        .all()
    )
    activity_by_day: Dict[str, Dict[str, int]] = {}
    for i in range(days):
        date = (datetime.utcnow() - timedelta(days=i)).date().isoformat()
        activity_by_day[date] = {"tasks": 0, "files": 0, "messages": 0}
    for task in tasks:
        date = task.created_at.date().isoformat()
        if date in activity_by_day:
            activity_by_day[date]["tasks"] += 1
    for file in files:
        date = file.created_at.date().isoformat()
        if date in activity_by_day:
            activity_by_day[date]["files"] += 1
    for message in messages:
        if message.role == "user":
            date = message.created_at.date().isoformat()
            if date in activity_by_day:
                activity_by_day[date]["messages"] += 1
    return {
        "period": f"Last {days} days",
        "activity": activity_by_day,
        "totals": {
            "tasks": len(tasks),
            "files": len(files),
            "messages": len([msg for msg in messages if msg.role == "user"]),
        },
    }


@app.get("/api/analytics/files")
async def get_file_analytics(current_user: User = Depends(get_current_user), db=Depends(get_db)):
    files = db.query(UploadedFile).filter(UploadedFile.user_id == current_user.id).all()
    type_breakdown: Dict[str, int] = {}
    total_size = 0
    for file in files:
        file_type = file.file_type
        type_breakdown[file_type] = type_breakdown.get(file_type, 0) + 1
        total_size += file.file_size
    project_breakdown: Dict[str, int] = {}
    for file in files:
        if file.project_id:
            project_breakdown[file.project_id] = project_breakdown.get(file.project_id, 0) + 1
    return {
        "total_files": len(files),
        "total_size_mb": round(total_size / (1024 * 1024), 2),
        "by_type": type_breakdown,
        "by_project": project_breakdown,
        "recent_uploads": [
            {
                "id": file.id,
                "filename": file.filename,
                "file_type": file.file_type,
                "created_at": file.created_at.isoformat(),
            }
            for file in sorted(files, key=lambda item: item.created_at, reverse=True)[:10]
        ],
    }


# ---------------------------------------------------------------------------
# Report endpoints
# ---------------------------------------------------------------------------


@app.get("/api/reports/project/{project_id}")
async def generate_project_report(
    project_id: str,
    current_user: User = Depends(get_current_user),
    db=Depends(get_db),
):
    project = (
        db.query(Project)
        .filter(Project.id == project_id, Project.user_id == current_user.id)
        .first()
    )
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    tasks = db.query(Task).filter(Task.project_id == project_id).all()
    alerts = db.query(Alert).filter(Alert.project_id == project_id).all()
    files = db.query(UploadedFile).filter(UploadedFile.project_id == project_id).all()
    total_tasks = len(tasks)
    completed_tasks = sum(1 for task in tasks if task.completed)
    overdue_tasks = sum(
        1
        for task in tasks
        if task.due_date and task.due_date < datetime.utcnow() and not task.completed
    )
    critical_alerts = sum(1 for alert in alerts if alert.severity == "critical")
    return {
        "report_generated": datetime.utcnow().isoformat(),
        "project": {
            "id": project.id,
            "name": project.name,
            "description": project.description,
            "status": project.status,
            "progress": project.progress,
            "created_at": project.created_at.isoformat(),
            "updated_at": project.updated_at.isoformat(),
        },
        "summary": {
            "total_tasks": total_tasks,
            "completed_tasks": completed_tasks,
            "pending_tasks": total_tasks - completed_tasks,
            "overdue_tasks": overdue_tasks,
            "completion_rate": round((completed_tasks / total_tasks * 100) if total_tasks else 0, 1),
            "total_alerts": len(alerts),
            "critical_alerts": critical_alerts,
            "total_files": len(files),
        },
        "tasks_detail": [
            {
                "id": task.id,
                "title": task.title,
                "priority": task.priority,
                "status": task.status,
                "completed": task.completed,
                "due_date": task.due_date.isoformat() if task.due_date else None,
                "created_at": task.created_at.isoformat(),
            }
            for task in tasks
        ],
        "alerts_detail": [
            {
                "id": alert.id,
                "title": alert.title,
                "severity": alert.severity,
                "created_at": alert.created_at.isoformat(),
            }
            for alert in alerts[:20]
        ],
    }


@app.get("/api/reports/weekly")
async def generate_weekly_report(current_user: User = Depends(get_current_user), db=Depends(get_db)):
    week_start = datetime.utcnow() - timedelta(days=7)
    projects = (
        db.query(Project)
        .filter(Project.user_id == current_user.id, Project.updated_at >= week_start)
        .all()
    )
    tasks = (
        db.query(Task)
        .filter(Task.user_id == current_user.id, Task.created_at >= week_start)
        .all()
    )
    completed_tasks = [task for task in tasks if task.completed]
    alerts = (
        db.query(Alert)
        .filter(Alert.user_id == current_user.id, Alert.created_at >= week_start)
        .all()
    )
    files = (
        db.query(UploadedFile)
        .filter(UploadedFile.user_id == current_user.id, UploadedFile.created_at >= week_start)
        .all()
    )
    return {
        "report_period": {
            "start": week_start.isoformat(),
            "end": datetime.utcnow().isoformat(),
            "days": 7,
        },
        "summary": {
            "projects_updated": len(projects),
            "tasks_created": len(tasks),
            "tasks_completed": len(completed_tasks),
            "alerts_generated": len(alerts),
            "files_uploaded": len(files),
        },
        "projects": [
            {
                "id": project.id,
                "name": project.name,
                "progress": project.progress,
                "status": project.status,
            }
            for project in projects
        ],
        "top_priorities": [
            {
                "id": task.id,
                "title": task.title,
                "priority": task.priority,
                "due_date": task.due_date.isoformat() if task.due_date else None,
            }
            for task in sorted(
                tasks,
                key=lambda item: (item.priority == "high", not item.completed),
                reverse=True,
            )[:5]
        ],
    }


@app.get("/api/reports/monthly")
async def generate_monthly_report(current_user: User = Depends(get_current_user), db=Depends(get_db)):
    month_start = datetime.utcnow() - timedelta(days=30)
    all_projects = db.query(Project).filter(Project.user_id == current_user.id).all()
    tasks = (
        db.query(Task)
        .filter(Task.user_id == current_user.id, Task.created_at >= month_start)
        .all()
    )
    all_tasks = db.query(Task).filter(Task.user_id == current_user.id).all()
    alerts = (
        db.query(Alert)
        .filter(Alert.user_id == current_user.id, Alert.created_at >= month_start)
        .all()
    )
    total_completion = sum(1 for task in all_tasks if task.completed)
    return {
        "report_period": {
            "start": month_start.isoformat(),
            "end": datetime.utcnow().isoformat(),
            "days": 30,
        },
        "overview": {
            "total_projects": len(all_projects),
            "active_projects": sum(1 for project in all_projects if project.status == "active"),
            "total_tasks": len(all_tasks),
            "tasks_created_this_month": len(tasks),
            "tasks_completed": total_completion,
            "overall_completion_rate": round((total_completion / len(all_tasks) * 100) if all_tasks else 0, 1),
            "alerts_this_month": len(alerts),
        },
        "project_performance": [
            {
                "id": project.id,
                "name": project.name,
                "progress": project.progress,
                "status": project.status,
            }
            for project in sorted(all_projects, key=lambda project: project.progress, reverse=True)
        ],
        "alert_breakdown": {
            "critical": sum(1 for alert in alerts if alert.severity == "critical"),
            "high": sum(1 for alert in alerts if alert.severity == "high"),
            "medium": sum(1 for alert in alerts if alert.severity == "medium"),
            "low": sum(1 for alert in alerts if alert.severity == "low"),
        },
    }


# ---------------------------------------------------------------------------
# Health check and root endpoints
# ---------------------------------------------------------------------------


@app.get("/api/health")
async def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "services": {
            "database": "connected",
            "openai": "available" if openai_client else "unavailable",
            "s3": "available" if s3_client else "unavailable",
            "websocket": f"{len(manager.active_connections)} active connections",
        },
    }


@app.get("/")
async def root():
    return {
        "message": "Diriyah Brain AI - Mobile Backend API",
        "version": "1.0.0",
        "docs": "/docs",
    }


# ---------------------------------------------------------------------------
# Startup hooks
# ---------------------------------------------------------------------------


@app.on_event("startup")
async def startup_event():
    logging.basicConfig(level=logging.INFO)
    logger.info("🚀 Starting Diriyah Mobile Backend API…")
    logger.info("Database: %s", DATABASE_URL)
    logger.info("OpenAI: %s", "✓" if openai_client else "✗")
    logger.info("S3: %s", "✓" if s3_client else "✗")
    logger.info("Uploads directory: %s", UPLOAD_DIR)


if __name__ == "__main__":  # pragma: no cover - manual execution helper
    import uvicorn

    port = int(os.getenv("PORT", "8000"))
    uvicorn.run(
        "backend.mobile_backend_api:app",
        host="0.0.0.0",
        port=port,
        reload=bool(os.getenv("UVICORN_RELOAD")),
        log_level="info",
    )

