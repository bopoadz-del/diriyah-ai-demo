import os
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
from google.oauth2.service_account import Credentials
SCOPES = ["https://www.googleapis.com/auth/drive.file"]
PROJECTS_ROOT_ID = os.getenv("PROJECTS_ROOT_ID")
def get_drive_service():
    creds = Credentials.from_service_account_file(os.getenv("GOOGLE_APPLICATION_CREDENTIALS"), scopes=SCOPES)
    return build("drive", "v3", credentials=creds)
def upload_to_drive(file):
    service = get_drive_service()
    file_metadata = {"name": file.filename}
    media = MediaIoBaseUpload(file.file, mimetype=file.content_type, resumable=True)
    uploaded = service.files().create(body=file_metadata, media_body=media, fields="id").execute()
    return uploaded.get("id")
def list_project_folders():
    service = get_drive_service()
    if not PROJECTS_ROOT_ID:
        return []
    query = f"'%s' in parents and mimeType = 'application/vnd.google-apps.folder'" % PROJECTS_ROOT_ID
    results = service.files().list(q=query, fields="files(id, name, mimeType)").execute()
    return results.get("files", [])
