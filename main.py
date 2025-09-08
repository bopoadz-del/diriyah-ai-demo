from fastapi import FastAPI, UploadFile, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn

from token_store import set_tokens, get_tokens
from files import process_file
from projects import fetch_projects          # ✅ dynamic import
from project_folders import list_mappings    # ✅ dynamic import

app = FastAPI(title="Diriyah Brain AI", version="1.0.0")

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    return {"message": "Welcome to Diriyah Brain AI!"}


@app.post("/set-tokens")
async def set_tokens_endpoint(openai_api_key: str = Form(...),
                              google_oauth: str = Form(None),
                              onedrive_oauth: str = Form(None)):
    set_tokens(openai_api_key, google_oauth, onedrive_oauth)
    return {"status": "tokens saved"}


@app.get("/get-tokens")
async def get_tokens_endpoint():
    return get_tokens()


@app.post("/upload-file")
async def upload_file(file: UploadFile):
    content = await file.read()
    result = process_file(file.filename, content)
    return {"status": "processed", "result": result}


@app.get("/projects")
async def get_projects():
    return {"projects": await fetch_projects()}   # ✅ always fresh


@app.get("/folders")
async def get_project_folders():
    return {"folders": list_mappings()}           # ✅ always fresh


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
