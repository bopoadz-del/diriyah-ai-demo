from backend.api.upload import router as upload_router
from backend.api.vision import router as vision_router
from backend.api.speech import router as speech_router

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

\1
app.include_router(speech_router, prefix="/api")
# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/healthz")
def healthz():
    return {"status": "ok"}

app.include_router(vision_router, prefix="/api")

app.include_router(upload_router, prefix="/api")
