from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
import os, io

SCOPES = ["https://www.googleapis.com/auth/drive"]
SERVICE_ACCOUNT_FILE = os.getenv("GOOGLE_SERVICE_ACCOUNT", "service_account.json")

def get_drive_service():
    creds = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE, scopes=SCOPES
    )
    return build("drive", "v3", credentials=creds)

def list_project_folders():
    service = get_drive_service()
    results = service.files().list(
        q="mimeType='application/vnd.google-apps.folder' and trashed=false",
        fields="files(id, name)"
    ).execute()
    return results.get("files", [])

def upload_file_to_project(project_folder_id: str, content_bytes: bytes, filename: str, mimetype: str):
    service = get_drive_service()
    media = MediaIoBaseUpload(io.BytesIO(content_bytes), mimetype=mimetype)
    file_metadata = {"name": filename, "parents": [project_folder_id]}
    return service.files().create(body=file_metadata, media_body=media, fields="id").execute()