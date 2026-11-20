from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ai_engine.intelligence.code_switch_detection import analyze as cs_analyze
from ai_engine.intelligence.language_detection import detect_text_language
from ai_engine.multilingual.translation import translation_service
from ai_engine.multilingual.transliteration import transliteration_service
from app.api.deps import get_current_user
from app.database.session import get_db
from app.models import Language, User
from app.schemas.languages import (
    DetectRequest,
    DetectResponse,
    LanguageOut,
    TranslateRequest,
    TranslateResponse,
    TransliterateRequest,
    TransliterateResponse,
)

router = APIRouter(prefix="/api/languages", tags=["languages"])


@router.get("", response_model=list[LanguageOut])
def list_languages(db: Session = Depends(get_db)) -> list[Language]:
    return db.query(Language).order_by(Language.sort_order, Language.code).all()


@router.get("/detect", response_model=DetectResponse)
def detect(text: str, base_language: str | None = None, _: User = Depends(get_current_user)) -> dict:
    if not text.strip():
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "text is required")
    verdict = detect_text_language(text, base_language)
    cs = cs_analyze(text, verdict.code)
    return {"verdict": verdict.to_dict(), "code_switching": cs.to_dict()}


@router.post("/detect", response_model=DetectResponse)
def detect_post(payload: DetectRequest, _: User = Depends(get_current_user)) -> dict:
    verdict = detect_text_language(payload.text, payload.base_language)
    cs = cs_analyze(payload.text, verdict.code)
    return {"verdict": verdict.to_dict(), "code_switching": cs.to_dict()}


@router.post("/translate", response_model=TranslateResponse)
async def translate(payload: TranslateRequest, _: User = Depends(get_current_user)) -> dict:
    result = await translation_service.translate(
        payload.text, payload.source_language, payload.target_language, payload.mode
    )
    return result.to_dict()


@router.post("/transliterate", response_model=TransliterateResponse)
async def transliterate(payload: TransliterateRequest, _: User = Depends(get_current_user)) -> dict:
    result = await transliteration_service.transliterate(
        payload.text, payload.source_language, payload.target_language
    )
    return result.to_dict()
