from fastapi import APIRouter
router = APIRouter()
@router.post("/auth/login")
def login(): return {"status": "ok", "token": "dummy-jwt"}
@router.post("/auth/register")
def register(): return {"status": "ok", "message": "User registered (stub)"}