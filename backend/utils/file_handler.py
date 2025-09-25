import tempfile, shutil
from fastapi import UploadFile

def save_upload_file_tmp(upload_file: UploadFile) -> str:
    """Save an UploadFile to a temporary file and return its path."""
    tmp = tempfile.NamedTemporaryFile(delete=False)
    with tmp as buffer:
        shutil.copyfileobj(upload_file.file, buffer)
    return tmp.name
