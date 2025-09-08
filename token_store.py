import os, json, time
from typing import Optional

PATH = os.getenv("TOKEN_STORE_PATH", "./tokens.json")

def _load():
    if not os.path.exists(PATH):
        return {}
    try:
        with open(PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def _save(d: dict):
    with open(PATH, "w", encoding="utf-8") as f:
        json.dump(d, f, indent=2)

def set_tokens(openai_api_key: str, google_oauth: Optional[str] = None, onedrive_oauth: Optional[str] = None):
    """
    Save tokens in a unified format expected by main.py
    """
    data = {
        "openai_api_key": openai_api_key,
        "google_oauth": google_oauth,
        "onedrive_oauth": onedrive_oauth,
    }
    _save(data)

def get_tokens() -> dict:
    """
    Retrieve tokens in the same format as stored by set_tokens
    """
    return _load()

def now_ts() -> int:
    return int(time.time())
