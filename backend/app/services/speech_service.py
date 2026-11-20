"""Speech orchestration: audio in -> routed transcription -> stored artefact.

This is the only place that combines the engine with the database.  It keeps the
honesty rules the UI depends on:

* ``engine_status`` is copied straight from the engine (ok / degraded /
  demo_fixture) and stored.
* ``confidence`` is stored together with ``confidence_source``; a NULL means "the
  model gave none and we could not estimate one", never a made-up number.
* Extra output modes are generated on demand, and each one records whether it
  actually succeeded.
"""
from __future__ import annotations

import uuid
from pathlib import Path
from typing import Dict, List, Optional

from sqlalchemy.orm import Session

from ai_engine.audio.noise_reduction import reduce_noise
from ai_engine.audio.vad import detect as run_vad
from ai_engine.base import AdapterError, AdapterUnavailable, AudioPayload
from ai_engine.intelligence.adaptive_router import AdaptiveRouter, RouterPolicy
from ai_engine.intelligence.code_switch_detection import segments_from_analysis
from ai_engine.intelligence.contextual_correction import apply_profile
from ai_engine.intelligence.language_detection import LANGUAGE_NAMES, detect_text_language
from ai_engine.intelligence.vocabulary_adaptation import (
    VocabEntry,
    apply_vocabulary,
    build_keyterms,
)
from ai_engine.multilingual.translation import translation_service
from ai_engine.multilingual.transliteration import transliteration_service
from app.config import BACKEND_DIR, settings
from app.core.logging import get_logger
from app.models import (
    AnalyticsEvent,
    ModelPrediction,
    RecordingMetadata,
    RoutingDecision,
    Transcription,
    TranscriptionSegment,
    User,
    UserVocabulary,
)
from app.schemas.speech import TranscribeOptions

log = get_logger("backend.speech")

AUDIO_DIR = BACKEND_DIR / "recordings"
_router: Optional[AdaptiveRouter] = None


def get_router() -> AdaptiveRouter:
    global _router
    if _router is None:
        _router = AdaptiveRouter(policy=RouterPolicy())
    return _router


def reset_router() -> None:
    global _router
    _router = None


def load_vocabulary(db: Session, user_id: str) -> List[VocabEntry]:
    rows = (
        db.query(UserVocabulary)
        .filter(UserVocabulary.user_id == user_id, UserVocabulary.is_active.is_(True))
        .order_by(UserVocabulary.weight.desc(), UserVocabulary.usage_count.desc())
        .all()
    )
    return [
        VocabEntry(
            word=r.word,
            preferred_spelling=r.preferred_spelling,
            category=r.category,
            language_code=r.language_code,
            pronunciation_hint=r.pronunciation_hint,
            weight=r.weight,
            usage_count=r.usage_count,
        )
        for r in rows
    ]


async def _generate_output(
    name: str, text: str, source_language: Optional[str], mode: str
) -> dict:
    """Produce one extra output variant, reporting failure honestly."""
    if name == "english":
        if mode == "translate":
            return {"text": text, "available": True, "method": "asr_translate_mode"}
        result = await translation_service.translate(text, source_language, "en-IN")
        return {"text": result.text or None, "available": result.available,
                "method": result.method, "provider": result.provider,
                "reason": result.reason}
    if name == "romanized":
        if mode == "translit":
            return {"text": text, "available": True, "method": "asr_translit_mode"}
        result = await transliteration_service.transliterate(text, source_language or "ta-IN", "en-IN")
        return {"text": result.text or None, "available": result.available,
                "method": result.method, "provider": result.provider,
                "reason": result.reason}
    if name == "native":
        if mode in ("transcribe", "codemix", "verbatim"):
            return {"text": text, "available": True, "method": "asr_native_script"}
        result = await transliteration_service.transliterate(text, "en-IN", source_language or "ta-IN")
        return {"text": result.text or None, "available": result.available,
                "method": result.method, "provider": result.provider,
                "reason": result.reason}
    return {"text": None, "available": False, "reason": f"unknown output '{name}'"}


async def transcribe_audio(
    db: Session,
    user: User,
    audio: AudioPayload,
    options: TranscribeOptions,
) -> dict:
    entries = load_vocabulary(db, user.id)
    keyterms = build_keyterms(entries)

    # ---- optional front-end processing -------------------------------
    processed = audio
    denoise_info = {"applied": False, "method": "none"}
    if options.noise_reduction:
        dn = reduce_noise(audio, enabled=True)
        processed = dn.audio
        denoise_info = dn.to_dict()
    vad = run_vad(processed)

    # ---- route --------------------------------------------------------
    router = get_router()
    try:
        outcome = await router.route(
            processed,
            mode=options.mode,
            language_code=options.language_code,
            keyterms=keyterms,
            context=options.context,
            prefer_model=options.prefer_model,
            vocabulary=[e.target for e in entries],
        )
    except AdapterUnavailable as exc:
        raise
    except AdapterError:
        raise

    result = outcome.result
    text = result.text

    # ---- vocabulary post-correction (guarded) -------------------------
    vocab_applied = []
    if entries:
        adaptation = apply_vocabulary(text, entries)
        if adaptation.applied:
            text = adaptation.text
            vocab_applied = adaptation.applied

    # ---- language + code-switch analysis ------------------------------
    verdict = detect_text_language(text, result.language)
    from ai_engine.intelligence.code_switch_detection import analyze as cs_analyze

    cs = cs_analyze(text, result.language)
    segments = segments_from_analysis(cs)

    # ---- context post-processing --------------------------------------
    preserve = [e.target for e in entries] + [t for t in keyterms]
    rewrite = apply_profile(text, options.context, preserve)
    professional_text = rewrite.text if options.context != "general" else None

    # ---- extra outputs -------------------------------------------------
    outputs: Dict[str, dict] = {}
    for name in options.include_outputs or []:
        outputs[name] = await _generate_output(name, text, result.language, options.mode)

    # ---- persist -------------------------------------------------------
    transcription = Transcription(
        user_id=user.id,
        title=options.title or (text[:60] + ("..." if len(text) > 60 else "") if text else "Untitled dictation"),
        original_text=text,
        native_text=(outputs.get("native") or {}).get("text") if options.mode not in ("transcribe", "codemix", "verbatim") else text,
        romanized_text=(outputs.get("romanized") or {}).get("text"),
        english_text=(outputs.get("english") or {}).get("text"),
        professional_text=professional_text,
        detected_languages=cs.languages,
        primary_language=verdict.code or result.language,
        is_code_mixed=cs.is_code_mixed,
        code_switch_count=cs.switch_count,
        duration_seconds=round(audio.duration_seconds, 2),
        word_count=len(text.split()),
        model_used=result.model,
        output_mode=options.mode,
        context_profile=options.context,
        status="completed" if text else "empty",
        engine_status=result.engine_status,
        confidence=outcome.confidence,
        confidence_source=outcome.confidence_source,
        latency_ms=outcome.total_latency_ms,
        audio_retained=bool(options.retain_audio),
    )
    db.add(transcription)
    db.flush()

    for idx, seg in enumerate(segments):
        db.add(
            TranscriptionSegment(
                transcription_id=transcription.id,
                index=idx,
                text=seg["text"],
                language=seg["language"],
                language_label=seg["language_name"],
                start_ms=seg["start_ms"],
                end_ms=seg["end_ms"],
                confidence=seg["confidence"],
                confidence_source=("proxy" if seg["confidence"] is not None else None),
                is_uncertain=seg["is_uncertain"],
                words=[w.to_dict() for w in (result.segments[idx].words if idx < len(result.segments) else [])],
            )
        )

    for pred in outcome.predictions:
        db.add(
            ModelPrediction(
                user_id=user.id,
                transcription_id=transcription.id,
                model_id=pred["model_id"],
                mode=pred["mode"],
                segment_scope=pred.get("scope", "full"),
                hypothesis_text=pred["hypothesis_text"],
                confidence=pred.get("confidence"),
                confidence_source=pred.get("confidence_source"),
                latency_ms=pred.get("latency_ms"),
                selected=pred.get("selected", False),
            )
        )

    db.add(
        RoutingDecision(
            user_id=user.id,
            transcription_id=transcription.id,
            primary_model=outcome.primary_model,
            alternatives_used=outcome.alternatives_used,
            escalated=outcome.escalated,
            needs_confirmation=outcome.needs_confirmation,
            reason=outcome.reason,
            policy=outcome.policy.to_dict(),
            trace=outcome.trace,
            latency_ms=outcome.total_latency_ms,
        )
    )

    audio_path = None
    if options.retain_audio:
        AUDIO_DIR.mkdir(parents=True, exist_ok=True)
        path = AUDIO_DIR / f"{transcription.id}.wav"
        path.write_bytes(audio.to_wav_bytes())
        audio_path = str(path)
        transcription.audio_path = audio_path

    db.add(
        RecordingMetadata(
            transcription_id=transcription.id,
            user_id=user.id,
            sample_rate=audio.sample_rate,
            channels=audio.channels,
            encoding=audio.encoding,
            duration_ms=int(audio.duration_seconds * 1000),
            peak_amplitude=audio.peak(),
            noise_level_db=denoise_info.get("noise_floor_dbfs"),
            vad_segments=[s.to_dict() for s in vad.segments],
            size_bytes=len(audio.data),
            retained=bool(options.retain_audio),
        )
    )
    db.add(
        AnalyticsEvent(
            user_id=user.id,
            event_type="transcription_completed",
            payload={
                "transcription_id": transcription.id,
                "model": result.model,
                "mode": options.mode,
                "engine_status": result.engine_status,
                "demo": result.demo,
                "escalated": outcome.escalated,
                "duration_seconds": round(audio.duration_seconds, 2),
                "word_count": len(text.split()),
                "languages": cs.languages,
            },
        )
    )

    # bump usage counts for vocabulary we actually applied
    if vocab_applied:
        applied_targets = {a["replaced_with"] for a in vocab_applied}
        for row in db.query(UserVocabulary).filter(UserVocabulary.user_id == user.id).all():
            if row.preferred_spelling in applied_targets:
                row.usage_count = (row.usage_count or 0) + 1

    db.commit()

    return {
        "id": transcription.id,
        "text": text,
        "mode": options.mode,
        "primary_language": verdict.code or result.language,
        "languages": cs.languages,
        "is_code_mixed": cs.is_code_mixed,
        "code_switch_count": cs.switch_count,
        "confidence": outcome.confidence,
        "confidence_source": outcome.confidence_source,
        "confidence_components": outcome.confidence_components,
        "engine_status": result.engine_status,
        "demo": result.demo,
        "model_used": result.model,
        "latency_ms": round(outcome.total_latency_ms, 1),
        "needs_confirmation": outcome.needs_confirmation,
        "segments": segments,
        "outputs": outputs,
        "routing": {
            "primary_model": outcome.primary_model,
            "alternatives_used": outcome.alternatives_used,
            "escalated": outcome.escalated,
            "reason": outcome.reason,
            "trace": outcome.trace,
            "policy": outcome.policy.to_dict(),
        },
        "audio": {
            "duration_seconds": round(audio.duration_seconds, 2),
            "peak": round(audio.peak(), 4),
            "dbfs": round(audio.dbfs(), 1),
            "vad": vad.to_dict(),
            "noise_reduction": denoise_info,
            "retained": bool(options.retain_audio),
        },
        "word_count": len(text.split()),
        "duration_seconds": round(audio.duration_seconds, 2),
        "message": None if result.engine_status != "demo_fixture" else (
            "Demo fixture: no speech provider is configured. This text is a fixed sample, not a recognition result."
        ),
    }


async def regenerate_output(db: Session, user: User, transcription: Transcription, kind: str) -> dict:
    text = transcription.original_text
    lang = transcription.primary_language
    out = await _generate_output(kind, text, lang, transcription.output_mode)
    if out.get("available") and out.get("text"):
        if kind == "english":
            transcription.english_text = out["text"]
        elif kind == "romanized":
            transcription.romanized_text = out["text"]
        elif kind == "native":
            transcription.native_text = out["text"]
        db.commit()
    return out


async def persist_streamed(
    db: Session,
    user: User,
    *,
    text: str,
    language: Optional[str],
    audio: AudioPayload,
    options: TranscribeOptions,
    model_label: str,
) -> dict:
    """Persist a transcript produced by the realtime socket.

    The realtime stream already ran the recogniser, so we do NOT call it again
    (that would double the cost for the same audio).  We still run every local
    analysis module: language ID, code-switch segmentation, vocabulary guard,
    context formatting and output generation.
    """
    from ai_engine.intelligence.code_switch_detection import analyze as cs_analyze

    entries = load_vocabulary(db, user.id)
    vocab_applied = []
    if entries:
        adaptation = apply_vocabulary(text, entries)
        if adaptation.applied:
            text = adaptation.text
            vocab_applied = adaptation.applied

    verdict = detect_text_language(text, language)
    cs = cs_analyze(text, language)
    segments = segments_from_analysis(cs)
    rewrite = apply_profile(text, options.context, [e.target for e in entries])

    outputs: Dict[str, dict] = {}
    for name in options.include_outputs or []:
        outputs[name] = await _generate_output(name, text, language, options.mode)

    transcription = Transcription(
        user_id=user.id,
        title=options.title or (text[:60] if text else "Live dictation"),
        original_text=text,
        native_text=text if options.mode in ("transcribe", "codemix", "verbatim") else (outputs.get("native") or {}).get("text"),
        romanized_text=(outputs.get("romanized") or {}).get("text"),
        english_text=(outputs.get("english") or {}).get("text"),
        professional_text=rewrite.text if options.context != "general" else None,
        detected_languages=cs.languages,
        primary_language=verdict.code or language,
        is_code_mixed=cs.is_code_mixed,
        code_switch_count=cs.switch_count,
        duration_seconds=round(audio.duration_seconds, 2),
        word_count=len(text.split()),
        model_used=model_label,
        output_mode=options.mode,
        context_profile=options.context,
        status="completed" if text else "empty",
        engine_status="ok",
        confidence=None,
        confidence_source=None,
        latency_ms=None,
        audio_retained=False,
    )
    db.add(transcription)
    db.flush()

    for idx, seg in enumerate(segments):
        db.add(
            TranscriptionSegment(
                transcription_id=transcription.id,
                index=idx,
                text=seg["text"],
                language=seg["language"],
                language_label=seg["language_name"],
                start_ms=seg["start_ms"],
                end_ms=seg["end_ms"],
                confidence=None,
                confidence_source=None,
                is_uncertain=seg["is_uncertain"],
                words=[],
            )
        )

    db.add(
        AnalyticsEvent(
            user_id=user.id,
            event_type="transcription_completed",
            payload={
                "transcription_id": transcription.id,
                "model": model_label,
                "mode": options.mode,
                "engine_status": "ok",
                "demo": False,
                "streaming": True,
                "duration_seconds": round(audio.duration_seconds, 2),
                "word_count": len(text.split()),
                "languages": cs.languages,
            },
        )
    )
    db.add(
        RecordingMetadata(
            transcription_id=transcription.id,
            user_id=user.id,
            sample_rate=audio.sample_rate,
            duration_ms=int(audio.duration_seconds * 1000),
            peak_amplitude=audio.peak(),
            size_bytes=len(audio.data),
            retained=False,
        )
    )
    db.commit()

    return {
        "id": transcription.id,
        "text": text,
        "mode": options.mode,
        "primary_language": verdict.code or language,
        "languages": cs.languages,
        "is_code_mixed": cs.is_code_mixed,
        "code_switch_count": cs.switch_count,
        "confidence": None,
        "confidence_source": None,
        "confidence_components": {},
        "engine_status": "ok",
        "demo": False,
        "model_used": model_label,
        "latency_ms": None,
        "needs_confirmation": False,
        "segments": segments,
        "outputs": outputs,
        "routing": {"primary_model": model_label, "alternatives_used": [],
                    "escalated": False, "reason": "streaming session", "trace": [],
                    "policy": {}},
        "audio": {"duration_seconds": round(audio.duration_seconds, 2),
                  "peak": round(audio.peak(), 4), "retained": False},
        "word_count": len(text.split()),
        "duration_seconds": round(audio.duration_seconds, 2),
        "message": "Streamed transcription: confidence is not reported by the realtime endpoint.",
    }
