from fastapi import APIRouter, Form
import json
from pathlib import Path
router=APIRouter()
F=Path(__file__).parent/'whatsapp_groups.json'

def load():
  return json.loads(F.read_text()) if F.exists() else {}

def save(d):
  F.write_text(json.dumps(d,indent=2,ensure_ascii=False))

@router.post('/whatsapp/register')
async def reg(user: str=Form(...), project: str=Form(...), group_id: str=Form(...)):
  d=load(); d.setdefault(user,{}).setdefault(project,[])
  if group_id not in d[user][project]: d[user][project].append(group_id)
  save(d); return {'status':'ok','groups':d[user][project]}

@router.get('/whatsapp/list')
async def lst(user: str, project: str):
  d=load(); return {'groups': d.get(user,{}).get(project,[])}
