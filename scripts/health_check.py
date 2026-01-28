#!/usr/bin/env python3
"""Health check script for Diriyah Brain AI backend."""

import os
import requests

BASE = os.getenv("API_BASE_URL", "http://localhost:8000")


def check_endpoint(path: str) -> tuple:
    """Check a single endpoint and return status code and response."""
    try:
        r = requests.get(BASE + path, timeout=5)
        return r.status_code, r.json()
    except Exception as e:
        return "ERR", str(e)


if __name__ == "__main__":
    print(f"Checking backend at: {BASE}\n")

    # Primary health endpoint
    status, data = check_endpoint("/health")
    print(f"/health      : {status} - {data}")

    # Kubernetes-style alias
    status, data = check_endpoint("/healthz")
    print(f"/healthz     : {status} - {data}")

    # API-prefixed endpoint (for frontend compatibility)
    status, data = check_endpoint("/api/health")
    print(f"/api/health  : {status} - {data}")
