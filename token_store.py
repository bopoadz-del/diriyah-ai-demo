import os, json, time
from typing import Optional

PATH = os.getenv("TOKEN_STORE_PATH", "./tokens.json")

def _load():
    if not os.path.exists(PATH): return {}
    try:
        with open(PATH,"r",encoding="utf-8") as f: return json.load(f)
    except Exception: return {}

def _save(d: dict):
    with open(PATH,"w",encoding="utf-8") as f: json.dump(d,f,indent=2)

def set_tokens(user_id: str, provider: str, tokens: dict):
    data = _load(); data.setdefault(user_id, {}); data[user_id][provider] = tokens; _save(data)

def get_tokens(user_id: str, provider: str) -> Optional[dict]:
    return _load().get(user_id, {}).get(provider)

def now_ts() -> int: return int(time.time())
