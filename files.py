import os, asyncio
from typing import List, Dict, Optional
from .token_store import get_tokens, set_tokens, now_ts

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

GOOGLE_SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]

def _g_service(creds: Credentials):
    return build("drive","v3",credentials=creds, cache_discovery=False)

def _mime_to_type(mime: str, name: str) -> str:
    mime, n = (mime or '').lower(), (name or '').lower()
    if 'spreadsheet' in mime or n.endswith(('.xlsx','.xls')): return 'excel'
    if 'pdf' in mime or n.endswith('.pdf'): return 'pdf'
    if mime.startswith('image/') or n.endswith(('.png','.jpg','.jpeg','.webp')): return 'image'
    if 'word' in mime or n.endswith(('.doc','.docx','.rtf')): return 'word'
    if 'csv' in mime or n.endswith('.csv'): return 'csv'
    return 'other'

def _time_ago(iso: str) -> str:
    from datetime import datetime, timezone
    try: dt = datetime.fromisoformat(iso.replace('Z','+00:00'))
    except Exception: return 'recently'
    sec = (datetime.now(timezone.utc) - dt).total_seconds()
    if sec < 60: return 'just now'
    if sec < 3600: return f"{int(sec//60)} minutes ago"
    if sec < 86400: return f"{int(sec//3600)} hours ago"
    if sec < 172800: return 'yesterday'
    return f"{int(sec//86400)} days ago"

async def _g_creds(user_id: str) -> Credentials:
    tokens = get_tokens(user_id,'google')
    if not tokens: raise RuntimeError('Google not connected')
    creds = Credentials(
        tokens.get('access_token'),
        refresh_token=tokens.get('refresh_token'),
        token_uri='https://oauth2.googleapis.com/token',
        client_id=os.getenv('GOOGLE_CLIENT_ID'),
        client_secret=os.getenv('GOOGLE_CLIENT_SECRET'),
        scopes=GOOGLE_SCOPES
    )
    if tokens.get('expires_at') and tokens['expires_at'] <= now_ts() + 60:
        from google.auth.transport.requests import Request
        await asyncio.to_thread(creds.refresh, Request())
        set_tokens(user_id,'google',{
            'access_token': creds.token,
            'refresh_token': creds.refresh_token or tokens.get('refresh_token'),
            'expires_at': int(creds.expiry.timestamp()) if creds.expiry else now_ts()+3000
        })
    return creds

async def google_recent_files(user_id: str, folder_id: Optional[str]=None) -> List[Dict]:
    creds = await _g_creds(user_id)
    service = await asyncio.to_thread(_g_service, creds)
    q = 'trashed=false' if not folder_id else f"'{folder_id}' in parents and trashed=false"
    res = await asyncio.to_thread(service.files().list,
        q=q, orderBy='modifiedTime desc', pageSize=10,
        fields='files(id,name,mimeType,modifiedTime,webViewLink)')
    res = res.execute()
    out = [{
        'id': f.get('id'),
        'name': f.get('name'),
        'type': _mime_to_type(f.get('mimeType',''), f.get('name','')),
        'updated': _time_ago(f.get('modifiedTime','')),
        'link': f.get('webViewLink')
    } for f in res.get('files', [])]
    return out

async def google_search_files(user_id: str, query: str, folder_id: Optional[str]=None) -> List[Dict]:
    creds = await _g_creds(user_id)
    service = await asyncio.to_thread(_g_service, creds)
    base = 'trashed=false'
    q = f"{base} and fullText contains '{query.replace('"','')}'"
    if folder_id: q = f"'{folder_id}' in parents and {q}"
    res = await asyncio.to_thread(service.files().list,
        q=q, orderBy='modifiedTime desc', pageSize=8,
        fields='files(id,name,mimeType,modifiedTime,webViewLink)')
    res = res.execute()
    out = [{
        'id': f.get('id'),
        'name': f.get('name'),
        'type': _mime_to_type(f.get('mimeType',''), f.get('name','')),
        'updated': _time_ago(f.get('modifiedTime','')),
        'link': f.get('webViewLink')
    } for f in res.get('files', [])]
    return out

async def fetch_recent_files(user_id: str, folder_id: Optional[str]=None) -> List[Dict]:
    return await google_recent_files(user_id, folder_id)

async def search_files(user_id: str, query: str, folder_id: Optional[str]=None) -> List[Dict]:
    return await google_search_files(user_id, query, folder_id)

async def search_files_in_folder(user_id: str, folder_id: str, query: str) -> List[Dict]:
    return await google_search_files(user_id, query, folder_id=folder_id)
