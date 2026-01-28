# scripts/seed_demo_data.py
import os
import requests

BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")

def seed_chat():
    r = requests.post(f"{BASE_URL}/api/chat", json={"message": "Hello, demo project team!"})
    print("Chat response:", r.json())

def seed_project():
    r = requests.post(f"{BASE_URL}/api/project/intel", json={"project": "Gateway1"})
    print("Project intel:", r.json())

def seed_cache():
    r = requests.get(f"{BASE_URL}/api/cache/status")
    print("Cache status:", r.json())

if __name__ == "__main__":
    seed_chat()
    seed_project()
    seed_cache()
    print("✅ Demo data seeded")
