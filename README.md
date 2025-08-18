# Diriyah AI (Render demo)

FastAPI app that:
- Connects to **Google Drive** (OAuth)
- **Indexes** PDFs / DOCX / XLSX / CSV to **ChromaDB**
- Answers questions with **OpenAI** using RAG

## 0) Prereqs
- OpenAI API key
- Google account
- Render account

## 1) Google Cloud setup (one-time)
1. Go to https://console.cloud.google.com/
2. Create a Project.
3. **APIs & Services → Library** → Enable **Google Drive API**.
4. **APIs & Services → OAuth consent screen**
   - User type: **External**
   - App name, email → Save
   - **Test users**: add your Google account.
5. **Credentials → Create credentials → OAuth client ID**
   - Application type: **Web application**
   - Authorized redirect URIs:
     - `https://YOUR-RENDER-URL/drive/callback`
     - (optional for local) `http://localhost:8000/drive/callback`
   - Copy **Client ID** & **Client Secret**.

## 2) Environment vars (Render → your service → Environment)
```env
OPENAI_API_KEY=sk-...
GOOGLE_OAUTH_CLIENT_ID=...
GOOGLE_OAUTH_CLIENT_SECRET=...
OAUTH_REDIRECT_URI=https://YOUR-RENDER-URL/drive/callback

# Fallbacks if Render blocks underscores
OPENAIAPIKEY=sk-...
GOOGLEOAUTHCLIENTID=...
GOOGLEOAUTHCLIENTSECRET=...
