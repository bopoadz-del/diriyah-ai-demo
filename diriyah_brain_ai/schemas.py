
from pydantic import BaseModel
from typing import Optional

class QueryRequest(BaseModel):
    query: str
    role: Optional[str] = None

class PhotoAnalyzeRequest(BaseModel):
    image_data: str  # base64 encoded


