"""
photos.py
---------

Endpoint to receive photo uploads from the client along with
geolocation metadata (latitude, longitude, elevation).  The uploaded
image is stored in a ``photos/`` directory and a JSON response is
returned with the coordinates.  This module could be extended to
trigger BIM updates or defect detection.

Endpoint:

POST /photos/upload

Body:
  - file: Uploaded image (JPEG/PNG)
  - coords: JSON string containing ``lat``, ``lon`` and optional
    ``elevation``

Returns:
  JSON with filename and coordinates
"""

from fastapi import APIRouter, UploadFile, Form
import shutil
import os
import json
from pathlib import Path

router = APIRouter()

PHOTO_DIR = Path(__file__).parent / "photos"
PHOTO_DIR.mkdir(exist_ok=True)

@router.post("/photos/upload")
async def upload_photo(file: UploadFile, coords: str = Form("{}")):
    try:
        coords_dict = json.loads(coords)
    except Exception:
        coords_dict = {}
    save_path = PHOTO_DIR / file.filename
    with open(save_path, "wb") as out:
        shutil.copyfileobj(file.file, out)
    return {
        "status": "ok",
        "filename": file.filename,
        "coords": coords_dict
    }