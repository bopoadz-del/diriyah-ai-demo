"""Translation endpoints powering Arabic localisation workflows."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict, Field, AliasChoices

from backend.services.translation_service import TranslationService

router = APIRouter()
_service = TranslationService()


class TranslationRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    text: str = Field(..., description="Text to translate")
    target_lang: str = Field(default="ar", validation_alias=AliasChoices("target_lang", "targetLang"))


class TranslationResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    translated: str
    target_lang: str = Field(alias="target_lang")


@router.post("/translate", response_model=TranslationResponse)
def translate_endpoint(payload: TranslationRequest) -> TranslationResponse:
    if not payload.text:
        raise HTTPException(status_code=400, detail="text is required")

    translated = _service.translate(payload.text, payload.target_lang)
    return TranslationResponse(translated=translated, target_lang=payload.target_lang)


__all__ = ["router"]
