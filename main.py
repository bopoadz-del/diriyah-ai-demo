import os, json, time
from fastapi import FastAPI, Request, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse, JSONResponse
from dotenv import load_dotenv
from openai import AsyncOpenAI

from adapters.token_store import set_tokens
from adapters.files import fetch_recent_files as files_fetch_recent, search_files as files_search, search_files_in_folder as files_search_in_folder
from adapters.projects import fetch_projects as projects_fetch
from adapters.project_folders import upsert_mapping, get_mapping as pf_get, list_mappings, delete_mapping

load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY: raise RuntimeError("Missing OPENAI_API_KEY")
client = AsyncOpenAI(api_key=OPENAI_API_KEY)

app = FastAPI(title="Diriyah AI Demo")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_user_id(): return "demo-user-001"

from google_auth_oauthlib.flow import Flow
@app.get("/auth/google/start")
def google_start():
    flow = Flow.from_client_config(
        {"web":{
            "client_id":os.getenv("GOOGLE_CLIENT_ID"),
            "client_secret":os.getenv("GOOGLE_CLIENT_SECRET"),
            "auth_uri":"https://accounts.google.com/o/oauth2/auth",
            "token_uri":"https://oauth2.googleapis.com/token",
            "redirect_uris":[os.getenv("GOOGLE_REDIRECT_URI")]
        }},
        scopes=["https://www.googleapis.com/auth/drive.readonly"]
    )
    flow.redirect_uri = os.getenv("GOOGLE_REDIRECT_URI")
    url, state = flow.authorization_url(access_type="offline", include_granted_scopes="true", prompt="consent")
    return RedirectResponse(url)

@app.get("/auth/google/callback")
def google_callback(request: Request):
    user_id = get_user_id()
    flow = Flow.from_client_config(
        {"web":{
            "client_id":os.getenv("GOOGLE_CLIENT_ID"),
            "client_secret":os.getenv("GOOGLE_CLIENT_SECRET"),
            "auth_uri":"https://accounts.google.com/o/oauth2/auth",
            "token_uri":"https://oauth2.googleapis.com/token",
            "redirect_uris":[os.getenv("GOOGLE_REDIRECT_URI")]
        }},
        scopes=["https://www.googleapis.com/auth/drive.readonly"]
    )
    flow.redirect_uri = os.getenv("GOOGLE_REDIRECT_URI")
    flow.fetch_token(authorization_response=str(request.url))
    creds = flow.credentials
    set_tokens(user_id,"google",{
        "access_token":creds.token,
        "refresh_token":creds.refresh_token,
        "expires_at": int(creds.expiry.timestamp()) if creds.expiry else int(time.time())+3000
    })
    return JSONResponse({"ok":True,"provider":"google"})

@app.get("/projects/folders")
def api_list_mappings(): return list_mappings()

@app.post("/projects/folders")
def api_upsert_mapping(payload: dict = Body(...)):
    req = ("project_name","provider","folder_id")
    if not all(k in payload for k in req):
        return {"ok":False,"error":"Missing required keys"}
    upsert_mapping(payload["project_name"], payload["provider"], payload["folder_id"], payload.get("display_name"))
    return {"ok":True}

@app.delete("/projects/folders")
def api_delete_mapping(project_name: str):
    delete_mapping(project_name); return {"ok":True}

TOOLS = [
    {"type":"function","function":{"name":"getProjects","description":"Return active projects.","parameters":{"type":"object","properties":{}}}},
    {"type":"function","function":{"name":"getRecentFiles","description":"Recent files; optional folder scope.","parameters":{"type":"object","properties":{"folder_id":{"type":"string"}}}}},
    {"type":"function","function":{"name":"searchFiles","description":"Search files by keyword; optional folder scope.","parameters":{"type":"object","properties":{"query":{"type":"string"},"folder_id":{"type":"string"}},"required":["query"]}}},
    {"type":"function","function":{"name":"searchFilesInFolder","description":"Search inside a specific folder.","parameters":{"type":"object","properties":{"folder_id":{"type":"string"},"query":{"type":"string"}},"required":["folder_id","query"]}}},
    {"type":"function","function":{"name":"getProjectFolder","description":"Look up folder mapping by project name.","parameters":{"type":"object","properties":{"project_name":{"type":"string"}},"required":["project_name"]}}}
]

async def tool_router(name: str, args: dict):
    user_id = get_user_id()
    if name == "getProjects": return await projects_fetch()
    if name == "getRecentFiles": return await files_fetch_recent(user_id=user_id, folder_id=(args or {}).get("folder_id"))
    if name == "searchFiles": return await files_search(user_id=user_id, query=(args or {}).get("query",""), folder_id=(args or {}).get("folder_id"))
    if name == "searchFilesInFolder": return await files_search_in_folder(user_id=user_id, folder_id=(args or {}).get("folder_id",""), query=(args or {}).get("query",""))
    if name == "getProjectFolder": 
        proj = (args or {}).get("project_name",""); mp = pf_get(proj)
        return {"found": bool(mp), **(mp or {})}
    raise ValueError("Unknown tool")

@app.post("/ai/query")
async def ai_query(payload: dict):
    question = (payload or {}).get("question") or "Quick project summary."
    context = (payload or {}).get("context")
    system_prompt = (
        "You are Diriyah AI, a concise Construction Q&A assistant. "
        "If a project name is given, call getProjectFolder(project_name) and prefer searchFilesInFolder. "
        "Return brief bullets and a 'Sources:' list with markdown links."
    )
    messages = [{"role":"system","content":system_prompt},{"role":"user","content":question}]
    if context: messages.append({"role":"user","content":f"Context: {json.dumps(context)}"})
    try:
        resp = await client.chat.completions.create(
            model="gpt-5-thinking",
            messages=messages, tools=TOOLS, tool_choice="auto", temperature=0.2
        )
        while True:
            msg = resp.choices[0].message
            if getattr(msg,"tool_calls",None):
                for call in msg.tool_calls:
                    args = json.loads(call.function.arguments or "{}")
                    result = await tool_router(call.function.name, args)
                    messages.append(msg)
                    messages.append({"role":"tool","tool_call_id":call.id,"name":call.function.name,"content":json.dumps(result)})
                resp = await client.chat.completions.create(model="gpt-5-thinking", messages=messages, temperature=0.2)
            else:
                return {"ok":True,"text": msg.content}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
def health(): return {"ok":True}
