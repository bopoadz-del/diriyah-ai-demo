# adapters/files.py
import os

def fetch_recent_files():
    """
    DEMO VERSION:
    Returns fake files until Google Drive API is fully connected.
    """
    return [
        {"name": "Demo Drawing.pdf", "id": "123"},
        {"name": "Demo Spec.docx", "id": "456"},
    ]
