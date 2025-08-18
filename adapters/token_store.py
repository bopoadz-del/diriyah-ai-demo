import os, json, time, base64
from typing import Optional
from cryptography.fernet import Fernet
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

PATH = os.getenv("TOKEN_STORE_PATH", "./tokens.json")
SECRET_KEY = os.getenv("TOKEN_ENCRYPTION_KEY", "default-secret-key")

def _derive_key():
    salt = b'diriyah_ai_salt_'
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=100000,
        backend=default_backend()
    )
    return base64.urlsafe_b64encode(kdf.derive(SECRET_KEY.encode()))

FERNET = Fernet(_derive_key())

def _load() -> dict:
    if not os.path.exists(PATH):
        return {}
    try:
        with open(PATH, "r", encoding="utf-8") as f:
            encrypted = f.read()
            return json.loads(FERNET.decrypt(encrypted.encode()).decode())
    except Exception:
        return {}

def _save(data: dict):
    encrypted = FERNET.encrypt(json.dumps(data).encode())
    with open(PATH, "w", encoding="utf-8") as f:
        f.write(encrypted.decode())

def set_tokens(user_id: str, provider: str, tokens: dict):
    data = _load()
    if user_id not in data:
        data[user_id] = {}
    data[user_id][provider] = tokens
    _save(data)

def get_tokens(user_id: str, provider: str) -> Optional[dict]:
    data = _load()
    return data.get(user_id, {}).get(provider)

def now_ts() -> int:
    return int(time.time())
