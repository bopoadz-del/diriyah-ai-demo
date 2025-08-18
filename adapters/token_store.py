import os, json, time, base64
from typing import Optional
from cryptography.fernet import Fernet
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

# Load configuration - use persistent storage path
PATH = os.getenv("TOKEN_STORE_PATH", "/var/data/tokens.json")
SECRET_KEY = os.getenv("TOKEN_ENCRYPTION_KEY")

if not SECRET_KEY:
    raise RuntimeError("Missing TOKEN_ENCRYPTION_KEY in environment")
if len(SECRET_KEY) < 32:
    raise ValueError("TOKEN_ENCRYPTION_KEY must be at least 32 characters")

# Key derivation
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

# Storage operations
def _load() -> dict:
    if not os.path.exists(PATH):
        return {}
    try:
        with open(PATH, "r", encoding="utf-8") as f:
            encrypted = f.read()
            return json.loads(FERNET.decrypt(encrypted.encode()).decode())
    except Exception as e:
        print(f"Token load error: {str(e)}")
        return {}

def _save(data: dict):
    # Ensure directory exists
    os.makedirs(os.path.dirname(PATH), exist_ok=True)
    encrypted = FERNET.encrypt(json.dumps(data).encode())
    with open(PATH, "w", encoding="utf-8") as f:
        f.write(encrypted.decode())

# Public interface
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
