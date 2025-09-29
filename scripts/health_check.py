
#!/usr/bin/env python3
import os, requests

BASE = os.getenv("API_BASE_URL", "http://localhost:8000")
def ok(path):
    try:
        r = requests.get(BASE+path, timeout=5)
        return r.status_code, r.json()
    except Exception as e:
        return "ERR", str(e)

if __name__ == "__main__":
    print("Health:", ok("/healthz"))
    print("Chat (not GET, just checking):", BASE + "/api/chat")
