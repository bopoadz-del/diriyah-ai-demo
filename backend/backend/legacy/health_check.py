#!/usr/bin/env python3
import os
from pathlib import Path

def check_env():
    print("🔍 Checking environment variables...")
    for var in ["OPENAI_API_KEY", "GOOGLE_SERVICE_ACCOUNT", "YOLO_MODEL"]:
        val = os.getenv(var)
        print(f"{var}: {'SET' if val else 'MISSING'}")

def check_folders():
    print("\n📂 Checking required folders...")
    for f in ["uploads", "images", "storage"]:
        p = Path(f)
        print(f"{f}: {'OK' if p.exists() else 'MISSING'}")

if __name__ == "__main__":
    check_env()
    check_folders()