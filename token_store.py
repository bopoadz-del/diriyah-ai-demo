"""
token_store.py
----------------

This module provides a minimal JSON‑based token store.  It can persist
arbitrary token strings keyed by user identifiers.  In this demo
application the token store is not used for the service account
credentials (those are configured via the environment), but it can be
repurposed to persist OpenAI keys or other secrets if needed.
"""

import json
from typing import Optional, Dict
from pathlib import Path

_STORE_FILE = Path("tokens.json")

def _load() -> Dict[str, str]:
    if _STORE_FILE.exists():
        try:
            with open(_STORE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def _save(data: Dict[str, str]) -> None:
    with open(_STORE_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f)

def save_token(user: str, token: str) -> None:
    data = _load()
    data[user] = token
    _save(data)

def get_token(user: str) -> Optional[str]:
    data = _load()
    return data.get(user)

def get_tokens() -> Dict[str, str]:
    return _load()