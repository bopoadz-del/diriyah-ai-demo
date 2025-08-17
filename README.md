# Diriyah AI (Demo)

Minimal ChatGPT-style app that answers questions and returns Google Drive links.

## Quick Deploy (Render + Google + OpenAI)

### 0) Fork or Upload this repo to your GitHub

### 1) Create an OpenAI API key
- Copy your key for later.

### 2) Create Google OAuth (for Google Drive access)
- https://console.cloud.google.com/
- Create project: **Diriyah AI Demo**
- Enable **Google Drive API**
- Credentials → **Create OAuth client ID** (Web Application)
- **Authorized redirect URI** (use your backend URL once you have it, for now put a placeholder e.g. https://example.com/auth/google/callback)
- Copy **Client ID** and **Client Secret**

> You will change the redirect URI after deploying the backend and you know your real Render URL.

### 3) Deploy Backend on Render (free)
- Create a **Web Service** from this repo.
- Render detects our **Dockerfile** (no build/start command needed).
- Add Environment Variables:
  - `OPENAI_API_KEY` = your key
  - `ACTIVE_FILES_PROVIDER` = `google`
  - `GOOGLE_CLIENT_ID` = from Google Console
  - `GOOGLE_CLIENT_SECRET` = from Google Console
  - `GOOGLE_REDIRECT_URI` = `https://YOUR-BACKEND.onrender.com/auth/google/callback` (update after Render gives URL)
  - `TOKEN_STORE_PATH` = `./tokens.json`
  - `PROJECT_FOLDER_STORE` = `./project_folders.json`

After deploy, you’ll get a URL like: `https://YOUR-BACKEND.onrender.com`.

Go back to **Google Console → Credentials → your OAuth client** and set the **Authorized redirect URI** exactly to:
```
https://YOUR-BACKEND.onrender.com/auth/google/callback
```

Update the same value in Render’s env var `GOOGLE_REDIRECT_URI` and **Restart** the service.

### 4) Deploy Static Site (the chat UI) on Render
- New → **Static Site**
- Repo: this repo
- **Publish Directory**: `web`
- No build command, no env vars.
- After deploy, you’ll get a URL like: `https://YOUR-FRONTEND.onrender.com`

Edit `web/index.html`, find:
```js
const API_BASE = 'http://localhost:8000';
```
Replace with your backend URL:
```js
const API_BASE = 'https://YOUR-BACKEND.onrender.com';
```
Commit and Render will auto-redeploy the static site.

### 5) Connect Google Drive
- Visit your frontend URL on your phone.
- Click **Google Drive** (left panel) to connect.
- Approve access (read-only).

### 6) (Optional) Map a Project Folder
- Find your Drive folder → copy the `<FOLDER_ID>` from the URL.
- Register it:
```
curl -X POST https://YOUR-BACKEND.onrender.com/projects/folders   -H "Content-Type: application/json"   -d '{"project_name":"Opera House – Foundation","provider":"google","folder_id":"<FOLDER_ID>","display_name":"Opera House – Foundation"}'
```

### 7) Ask a Question
Example:
```
Find the latest method statements in Opera House – Foundation and share links.
```

You’ll get a short answer + **Sources** with Drive links.

---

## Local Dev (optional)
```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # fill in values
uvicorn main:app --reload --port 8000
# then open web/index.html and set API_BASE to http://localhost:8000
```

## Files
- `main.py` — FastAPI backend (Google Drive OAuth + chat tools)
- `adapters/` — Google Drive + token + mapping helpers
- `web/index.html` — Diriyah-themed chat UI
- `Dockerfile` — backend container
- `requirements.txt` — Python deps
- `.env.example` — template env file
- `docker-compose.yml` (local optional)
- `nginx.conf` (local optional)
