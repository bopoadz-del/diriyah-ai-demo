
from fastapi import APIRouter
router = APIRouter()

@router.get("/")
def index():
    return {"msg": "bim.py endpoint working"}
