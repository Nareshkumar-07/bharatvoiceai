"""Aggregated engine status and routing metrics for the AI Intelligence screen."""
from __future__ import annotations

from typing import Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from ai_engine.adapters.sarvam.cost import sarvam_usage
from ai_engine.base import AdapterUnavailable
from ai_engine.multilingual.translation import translation_service
from ai_engine.multilingual.transliteration import transliteration_service
from ai_engine.registry import availability_report, build_adapters, primary_adapter
from app.config import settings
from app.models import ModelPrediction, RoutingDecision, Transcription
from app.services.speech_service import get_router


async def status_payload() -> dict:
    report = await availability_report()
    primary, reason = await primary_adapter()
    primary_id = primary.model_id if primary else None
    for item in report:
        item["is_primary"] = item["model_id"] == primary_id

    notes = []
    if not settings.sarvam_configured:
        notes.append("SARVAM_API_KEY is not set: Saaras v4 (the primary recogniser) cannot run.")
    if not any(m["available"] for m in report if m["model_id"] != "demo-fixture"):
        notes.append("No real recognition backend is available. Set SARVAM_API_KEY, or enable a "
                     "local model, or set DEMO_MODE=true to explore the UI with clearly badged fixtures.")
    if settings.demo_mode:
        notes.append("DEMO_MODE is on: fixture transcripts are possible and always labelled.")
    notes.append("Saaras v4 does not return per-word confidence; scores shown as 'proxy' are our "
                 "own estimate and are not calibrated until fitted on evaluation data.")

    return {
        "primary_engine": primary_id,
        "primary_available": primary is not None,
        "primary_unavailable_reason": reason,
        "streaming_available": bool(settings.sarvam_configured),
        "demo_mode": settings.demo_mode,
        "models": report,
        "translation": translation_service.status(),
        "transliteration": transliteration_service.status(),
        "usage": sarvam_usage.snapshot(),
        "capabilities": {
            "rest_transcription": any(m["available"] for m in report if m["model_id"] != "demo-fixture"),
            "realtime_streaming": bool(settings.sarvam_configured),
            "code_switch_detection": True,
            "adaptive_routing": get_router().policy.enabled,
            "vocabulary_adaptation": True,
            "offline_recognition": any(
                m["available"] and m["runtime"] == "local" for m in report
            ),
        },
        "notes": notes,
    }


def router_metrics(db: Session, user_id: str) -> dict:
    decisions = db.query(RoutingDecision).filter(RoutingDecision.user_id == user_id).all()
    router = get_router()
    total = len(decisions)
    escalations = sum(1 for d in decisions if d.escalated)
    confirmations = sum(1 for d in decisions if d.needs_confirmation)
    latencies = [d.latency_ms for d in decisions if d.latency_ms is not None]

    model_usage: dict[str, int] = {}
    for d in decisions:
        model_usage[d.primary_model] = model_usage.get(d.primary_model, 0) + 1

    predictions = db.query(ModelPrediction).filter(ModelPrediction.user_id == user_id).count()
    calib = router.calibrator

    return {
        "decisions": total,
        "escalations": escalations,
        "escalation_rate": round(escalations / total, 3) if total else None,
        "confirmation_requests": confirmations,
        "average_latency_ms": round(sum(latencies) / len(latencies), 1) if latencies else None,
        "model_usage": model_usage,
        "predictions_logged": predictions,
        "policy": router.policy.to_dict(),
        "calibration": {
            "fitted": bool(calib and calib.is_fitted),
            "samples": calib.samples if calib else 0,
            "note": "Proxy scores are uncalibrated until a calibrator is fitted on labelled evaluation data.",
        },
        "has_data": total > 0,
    }


def evaluation_summary(db: Session, user_id: str) -> dict:
    """WER/CER are only real when you supply reference transcripts."""
    total = db.query(Transcription).filter(
        Transcription.user_id == user_id, Transcription.deleted_at.is_(None)
    ).count()
    return {
        "available": False,
        "reason": (
            "WER, CER, language-ID accuracy and code-switch accuracy require reference "
            "transcripts. Run `python scripts/run_evaluation.py --manifest eval/manifest.jsonl` "
            "and the report is stored under evaluation/reports/."
        ),
        "report": None,
        "wer": None,
        "cer": None,
        "rows": [],
        "notes": [
            f"{total} transcription(s) are stored, but stored audio alone cannot be scored "
            "without references.",
            "Metrics are never estimated or inferred in this API.",
        ],
    }
