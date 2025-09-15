from fastapi import FastAPI, UploadFile, Form
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn, os, json
from pathlib import Path
from diriyah_brain_ai.whatsapp_adapter import router as wa_router
from diriyah_brain_ai.teams import router as teams_router
from diriyah_brain_ai.drive_adapter import list_recent_files, search_files

BASE_DIR = Path(__file__).parent.resolve()
STATIC_DIR = BASE_DIR / 'diriyah_brain_ai' / 'static'
INDEX_HTML = BASE_DIR / 'diriyah_brain_ai' / 'index.html'
PROJECTS_JSON = BASE_DIR / 'diriyah_brain_ai' / 'projects.json'

app=FastAPI()
app.add_middleware(CORSMiddleware,allow_origins=['*'],allow_credentials=True,allow_methods=['*'],allow_headers=['*'])
app.mount('/diriyah_brain_ai/static', StaticFiles(directory=str(STATIC_DIR)), name='static')

@app.get('/')
def root(): return FileResponse(str(INDEX_HTML))

@app.get('/projects/list')
def projects_list():
  with open(PROJECTS_JSON,'r',encoding='utf-8') as f: projects=json.load(f)
  return {'projects':[{'name':k,**v} for k,v in projects.items()]}

@app.post('/ai/query')
async def ai_query(query: str = Form(...), role: str = Form(None)):
  return {'reply': f"AI ({role or 'default'}): I received your query: {query}"}

@app.post('/upload-file')
async def upload_file(file: UploadFile):
  path=str(BASE_DIR / 'uploads')
  os.makedirs(path, exist_ok=True)
  out = os.path.join(path, file.filename)
  with open(out,'wb') as fh: fh.write(await file.read())
  return {'status':'ok','saved':out}

@app.get('/drive/files')
def drive_files(project: str): return {'files': list_recent_files(project)}
@app.get('/drive/search')
def drive_search(project: str, q: str): return {'matches': search_files(project,q)}

app.include_router(wa_router)
app.include_router(teams_router)

if __name__=='__main__':
  uvicorn.run(app,host='0.0.0.0',port=8080)
