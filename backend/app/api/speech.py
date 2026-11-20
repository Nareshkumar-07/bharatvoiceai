from __future__ import annotations

import time
from collections import defaultdict, deque
from typing import Deque, Dict, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from ai_engine.adapters.sarvam.cost import sarvam_usage
from ai_engine.base import AdapterError, AdapterUnavailable
from app.api.deps import get_current_user
from app.config import settings
from app.database.session import get_db
from app.models import User
from app.schemas.speech import SpeechResult
from app.services.audio_io import AudioDecodeError, decode_audio
from app.services.speech_service import transcribe_audio

router = APIRouter(prefix="/api/speech", tags=["speech"])

_hits: Dict[str, Deque[float]] = defaultdict(deque)


def _rate_limit(user_id: str) -> None:
    now = time.time()
    window = _hits[user_id]
    while window and now - window[0] > 60:
        window.popleft()
    if len(window) >= settings.rate_limit_transcribe_per_minute:
        raise HTTPException(
            status.HTTP_429_TOO_MANY_REQUESTS,
            f"Rate limit: {settings.rate_limit_transcribe_per_minute} transcriptions per minute",
        )
    window.append(now)


def _validate_mode(mode: str) -> str:
    allowed = {"transcribe", "codemix", "translit", "translate", "verbatim"}
    if mode not in allowed:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, f"mode must be one of {sorted(allowed)}")
    return mode


async def _handle(
    db: Session,
    user: User,
    file: UploadFile,
    mode: str,
    context: str,
    language_code: Optional[str],
    prefer_model: Optional[str],
    include_outputs: str,
    noise_reduction: bool,
    title: Optional[str],
    retain_audio: bool,
) -> dict:
    _rate_limit(user.id)
    _validate_mode(mode)

    raw = await file.read()
    if not raw:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Empty audio upload")
    if len(raw) > settings.max_upload_mb * 1024 * 1024:
        raise HTTPException(
            status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            f"Audio exceeds {settings.max_upload_mb} MB",
        )

    try:
        audio = decode_audio(raw, file.filename or "audio.wav")
    except AudioDecodeError as exc:
        raise HTTPException(status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, str(exc)) from exc

    if audio.duration_seconds > settings.max_recording_seconds:
        raise HTTPException(
            status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            f"Recording exceeds {settings.max_recording_seconds}s limit",
        )

    outputs = [o.strip() for o in (include_outputs or "native").split(",") if o.strip()]
    from app.schemas.speech import TranscribeOptions

    options = TranscribeOptions(
        mode=mode,
        context=context,
        language_code=language_code,
        prefer_model=prefer_model,
        include_outputs=outputs,
        noise_reduction=noise_reduction,
        title=title,
        retain_audio=retain_audio,
    )

    try:
        result = await transcribe_audio(db, user, audio, options)
    except AdapterUnavailable as exc:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            {
                "error": "no_recognition_backend",
                "message": str(exc),
                "hint": "Set SARVAM_API_KEY on the backend, enable a local model, or set DEMO_MODE=true.",
            },
        ) from exc
    except AdapterError as exc:
        raise HTTPException(
            exc.status_code if 400 <= exc.status_code < 600 else 502,
            {"error": "recognition_failed", "message": str(exc), "retryable": exc.retryable},
        ) from exc

    sarvam_usage.record(audio.duration_seconds, failed=False)
    return result


@router.post("/transcribe", response_model=SpeechResult)
async def transcribe(
    file: UploadFile = File(...),
    mode: str = Form("transcribe"),
    context: str = Form("general"),
    language_code: Optional[str] = Form(None),
    prefer_model: Optional[str] = Form(None),
    include_outputs: str = Form("native"),
    noise_reduction: bool = Form(False),
    title: Optional[str] = Form(None),
    retain_audio: bool = Form(False),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    return await _handle(db, user, file, mode, context, language_code, prefer_model,
                         include_outputs, noise_reduction, title, retain_audio)


@router.post("/upload", response_model=SpeechResult)
async def upload(
    file: UploadFile = File(...),
    mode: str = Form("transcribe"),
    context: str = Form("general"),
    language_code: Optional[str] = Form(None),
    include_outputs: str = Form("native"),
    retain_audio: bool = Form(False),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    """Batch-style upload for longer files (same pipeline, no live socket)."""
    return await _handle(db, user, file, mode, context, language_code, None,
                         include_outputs, False, None, retain_audio)
