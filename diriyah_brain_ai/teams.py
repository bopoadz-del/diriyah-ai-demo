from fastapi import APIRouter, Form
router=APIRouter()
ACTIVE={}
@router.post('/teams/connect')
async def connect(user: str=Form(...), project: str=Form(...), channel_id: str=Form(...)):
  ACTIVE[user]={'project':project,'channel_id':channel_id}; return {'status':'connected','info':ACTIVE[user]}
@router.post('/teams/disconnect')
async def disconnect(user: str=Form(...)):
  ACTIVE.pop(user, None); return {'status':'disconnected'}
@router.get('/teams/status')
async def status(user: str):
  return ACTIVE.get(user, {'status':'not connected'})
