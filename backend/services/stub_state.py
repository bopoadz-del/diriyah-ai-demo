"""Lightweight in-memory store used by Render preview deployments.

The production system persists projects, chats and analytics to external
services.  For preview environments we keep everything in process so the
React frontend can exercise flows without additional infrastructure.
"""

from __future__ import annotations

import itertools
import threading
from collections.abc import Iterable
from datetime import datetime
from typing import Any, Dict, List, Optional

__all__ = [
    "add_message",
    "add_user",
    "apply_message_action",
    "ensure_project",
    "get_chat",
    "get_message",
    "get_or_create_default_chat",
    "get_project",
    "list_analytics",
    "list_chats",
    "list_messages",
    "list_projects",
    "list_users",
    "log_action",
    "log_upload",
    "pin_chat",
    "rename_chat",
    "seed_projects",
    "summarise_chat",
    "sync_drive_project",
    "unpin_chat",
    "update_message",
]

_lock = threading.RLock()
_project_seq = itertools.count(1)
_chat_seq = itertools.count(1)
_message_seq = itertools.count(1)
_analytics_seq = itertools.count(1)
_user_seq = itertools.count(1)

_projects: Dict[str, Dict[str, Any]] = {}
_drive_index: Dict[str, str] = {}
_project_chats: Dict[str, List[Dict[str, Any]]] = {}
_chat_index: Dict[int, str] = {}
_chat_messages: Dict[int, List[Dict[str, Any]]] = {}
_message_index: Dict[int, Dict[str, Any]] = {}
_analytics: List[Dict[str, Any]] = []
_users: List[Dict[str, Any]] = []


def _timestamp() -> str:
    return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


def _copy(payload: Dict[str, Any]) -> Dict[str, Any]:
    return {**payload}


def _seed_user(name: str, email: str, role: str) -> None:
    with _lock:
        _users.append(
            {
                "id": next(_user_seq),
                "name": name,
                "email": email,
                "role": role,
            }
        )


for _name, _email, _role in (
    ("Aisha Al Saud", "aisha.alsaud@example.com", "Program Director"),
    ("Fahad Al Mutairi", "fahad.mutairi@example.com", "Project Engineer"),
    ("Noura Al Ghamdi", "noura.ghamdi@example.com", "Commercial Manager"),
):
    _seed_user(_name, _email, _role)


def seed_projects(fixtures: Dict[str, Dict[str, Any]]) -> None:
    """Ensure fixture projects exist within the in-memory store."""

    with _lock:
        for project_id, payload in fixtures.items():
            if project_id not in _projects:
                _projects[project_id] = _copy(payload)
                drive_id = payload.get("drive_id")
                if drive_id:
                    _drive_index[drive_id] = project_id
            _project_chats.setdefault(project_id, [])
            if not _project_chats[project_id]:
                chat = create_chat(project_id, title=f"{payload['name']} Updates")
                add_message(
                    chat["id"],
                    role="assistant",
                    content=(
                        "Welcome to the Diriyah Brain preview. This chat streams "
                        "status updates, design highlights and next steps for the project."
                    ),
                )


def ensure_project(project: Dict[str, Any]) -> Dict[str, Any]:
    """Register a project dictionary and return the stored copy."""

    project_id = str(project["id"])
    with _lock:
        stored = _projects.get(project_id)
        if stored:
            stored.update({k: v for k, v in project.items() if k != "id"})
        else:
            stored = {**project}
            _projects[project_id] = stored
        drive_id = stored.get("drive_id")
        if drive_id:
            _drive_index[drive_id] = project_id
        _project_chats.setdefault(project_id, [])
        return _copy(stored)


def sync_drive_project(*, drive_id: str, name: str) -> Dict[str, Any]:
    """Create or update a project originating from Google Drive metadata."""

    with _lock:
        project_id = _drive_index.get(drive_id)
        if project_id is None:
            project_id = f"drive-{next(_project_seq):03d}"
            stored = {
                "id": project_id,
                "name": name,
                "drive_id": drive_id,
                "status": "Synced",
                "location": "Imported from Drive",
                "progress_percent": 35,
                "next_milestone": "Review uploaded documents",
                "summary": (
                    "Auto-generated project imported from Drive folder metadata. "
                    "Replace with live project information when available."
                ),
            }
            _projects[project_id] = stored
            _drive_index[drive_id] = project_id
            _project_chats.setdefault(project_id, [])
        else:
            stored = _projects[project_id]
            stored["name"] = name
            stored.setdefault("drive_id", drive_id)
        return _copy(stored)


def list_projects() -> List[Dict[str, Any]]:
    with _lock:
        return [_copy(project) for project in _projects.values()]


def get_project(project_id: str) -> Optional[Dict[str, Any]]:
    with _lock:
        project = _projects.get(str(project_id))
        return _copy(project) if project else None


def list_users() -> List[Dict[str, Any]]:
    with _lock:
        return [_copy(user) for user in _users]


def add_user(*, name: str, email: str, role: str = "Project Engineer") -> Dict[str, Any]:
    with _lock:
        user = {
            "id": next(_user_seq),
            "name": name,
            "email": email,
            "role": role,
        }
        _users.append(user)
        return _copy(user)


def _next_chat_title(project_id: str) -> str:
    project = _projects.get(project_id)
    base = project["name"] if project else "Project"
    return f"{base} Chat {next(_chat_seq)}"


def _register_chat(project_id: str, chat: Dict[str, Any]) -> None:
    chat_id = chat["id"]
    _project_chats[project_id].append(chat)
    _chat_index[chat_id] = project_id
    _chat_messages.setdefault(chat_id, [])


def create_chat(project_id: str, *, title: Optional[str] = None) -> Dict[str, Any]:
    project_id = str(project_id)
    with _lock:
        if project_id not in _projects:
            raise KeyError(f"Unknown project {project_id}")
        chat = {
            "id": next(_chat_seq),
            "project_id": project_id,
            "title": title or _next_chat_title(project_id),
            "pinned": False,
            "created_at": _timestamp(),
            "updated_at": _timestamp(),
        }
        _register_chat(project_id, chat)
        return _copy(chat)


def get_chat(chat_id: int) -> Optional[Dict[str, Any]]:
    with _lock:
        project_id = _chat_index.get(chat_id)
        if project_id is None:
            return None
        for chat in _project_chats.get(project_id, []):
            if chat["id"] == chat_id:
                return _copy(chat)
        return None


def list_chats(project_id: str) -> List[Dict[str, Any]]:
    project_id = str(project_id)
    with _lock:
        chats = list(_project_chats.get(project_id, []))
        return sorted(
            (_copy(chat) for chat in chats),
            key=lambda chat: (
                not chat.get("pinned", False),
                chat.get("created_at", ""),
            ),
        )


def rename_chat(chat_id: int, *, title: str) -> Optional[Dict[str, Any]]:
    with _lock:
        project_id = _chat_index.get(chat_id)
        if project_id is None:
            return None
        for chat in _project_chats.get(project_id, []):
            if chat["id"] == chat_id:
                chat["title"] = title
                chat["updated_at"] = _timestamp()
                return _copy(chat)
        return None


def pin_chat(chat_id: int, *, pinned: bool) -> Optional[Dict[str, Any]]:
    with _lock:
        project_id = _chat_index.get(chat_id)
        if project_id is None:
            return None
        for chat in _project_chats.get(project_id, []):
            if chat["id"] == chat_id:
                chat["pinned"] = pinned
                chat["updated_at"] = _timestamp()
                return _copy(chat)
        return None


def unpin_chat(chat_id: int) -> Optional[Dict[str, Any]]:
    return pin_chat(chat_id, pinned=False)


def list_messages(chat_id: int) -> List[Dict[str, Any]]:
    with _lock:
        messages = _chat_messages.get(chat_id, [])
        return [_copy(message) for message in messages]


def get_message(message_id: int) -> Optional[Dict[str, Any]]:
    with _lock:
        message = _message_index.get(message_id)
        return _copy(message) if message else None


def _auto_title(content: str) -> str:
    words = [word for word in content.strip().split() if word]
    if not words:
        return "New Chat"
    snippet = " ".join(words[:6])
    return snippet[:60].title()


def add_message(chat_id: int, *, role: str, content: str) -> Dict[str, Any]:
    with _lock:
        if chat_id not in _chat_messages:
            _chat_messages[chat_id] = []
        message = {
            "id": next(_message_seq),
            "chat_id": chat_id,
            "role": role,
            "content": content,
            "created_at": _timestamp(),
            "liked": False,
            "disliked": False,
            "copied": False,
            "read": False,
            "shared": False,
        }
        _chat_messages[chat_id].append(message)
        _message_index[message["id"]] = message

        project_id = _chat_index.get(chat_id)
        if project_id is not None:
            for chat in _project_chats.get(project_id, []):
                if chat["id"] == chat_id:
                    chat["updated_at"] = message["created_at"]
                    if role == "user" and len(_chat_messages[chat_id]) == 1:
                        chat["title"] = _auto_title(content)
                    break
        return _copy(message)


def update_message(message_id: int, *, content: str) -> Optional[Dict[str, Any]]:
    with _lock:
        message = _message_index.get(message_id)
        if message is None:
            return None
        message["content"] = content
        message["updated_at"] = _timestamp()
        return _copy(message)


def apply_message_action(message_id: int, *, action: str, user_id: int) -> Optional[Dict[str, Any]]:
    with _lock:
        message = _message_index.get(message_id)
        if message is None:
            return None
        if action == "like":
            message["liked"] = True
        elif action == "dislike":
            message["disliked"] = True
        elif action == "copy":
            message["copied"] = True
        elif action == "read":
            message["read"] = True
        elif action == "share":
            message["shared"] = True
        log_action(action=action, user_id=user_id, message_id=message_id)
        return _copy(message)


def log_action(
    *,
    action: str,
    user_id: int,
    message_id: Optional[int] = None,
    detail: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    with _lock:
        entry = {
            "id": next(_analytics_seq),
            "action": action,
            "user_id": user_id,
            "message_id": message_id,
            "detail": detail or {},
            "timestamp": _timestamp(),
        }
        _analytics.append(entry)
        return _copy(entry)


def log_upload(
    *, project_id: str, file_name: str, chat_id: Optional[int], drive_folder_id: Optional[str]
) -> None:
    log_action(
        action="upload",
        user_id=1,
        detail={
            "project_id": str(project_id),
            "file_name": file_name,
            "chat_id": chat_id,
            "drive_folder_id": drive_folder_id,
        },
    )


def list_analytics() -> List[Dict[str, Any]]:
    with _lock:
        return [_copy(entry) for entry in _analytics]


def summarise_chat(chat_id: int) -> str:
    messages = list_messages(chat_id)
    if not messages:
        return "No conversation history yet."
    highlights = messages[-3:]
    summary_lines = [
        "Conversation summary:",
        *(f"- {item['role'].title()}: {item['content']}" for item in highlights),
    ]
    user_messages = [item for item in messages if item["role"] == "user"]
    if user_messages:
        summary_lines.append(
            f"Next step: follow up on '{user_messages[-1]['content']}'"
        )
    return "\n".join(summary_lines)


def list_messages_iterable(chat_id: int) -> Iterable[Dict[str, Any]]:
    with _lock:
        return list(_chat_messages.get(chat_id, []))


def get_or_create_default_chat(project_id: str) -> Dict[str, Any]:
    project_id = str(project_id)
    with _lock:
        chats = _project_chats.get(project_id)
        if not chats:
            return create_chat(project_id)
        return _copy(chats[0])
