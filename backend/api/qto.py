from fastapi import APIRouter, Query
from backend.services.qto_pipeline import generate_qto

router = APIRouter()

@router.get('/qto')
def get_qto(file_id: str = Query(...), mime_type: str = Query(...)):
    try:
        result = generate_qto(file_id, mime_type)
        return {'status': 'ok', 'quantities': result}
    except Exception as e:
        return {'status': 'error', 'message': str(e)}
