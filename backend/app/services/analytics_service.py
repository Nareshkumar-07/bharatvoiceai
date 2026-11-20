"""Analytics computed from stored rows only - no synthetic numbers."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Dict, List

from sqlalchemy import func
from sqlalchemy.orm import Session

from ai_engine.intelligence.language_detection import LANGUAGE_NAMES
from app.models import AnalyticsEvent, Transcription, UserCorrection, UserVocabulary


def _base_query(db: Session, user_id: str):
    return db.query(Transcription).filter(
        Transcription.user_id == user_id, Transcription.deleted_at.is_(None)
    )


def overview(db: Session, user_id: str) -> dict:
    q = _base_query(db, user_id)
    total = q.count()
    if total == 0:
        return {
            "total_transcriptions": 0, "total_words": 0, "total_duration_seconds": 0.0,
            "code_mixed_percentage": 0.0, "average_correction_rate": None,
            "languages_used": 0, "current_streak_days": 0, "words_this_week": 0,
            "has_data": False,
        }

    words = db.query(func.coalesce(func.sum(Transcription.word_count), 0)).filter(
        Transcription.user_id == user_id, Transcription.deleted_at.is_(None)
    ).scalar()
    duration = db.query(func.coalesce(func.sum(Transcription.duration_seconds), 0.0)).filter(
        Transcription.user_id == user_id, Transcription.deleted_at.is_(None)
    ).scalar()
    mixed = q.filter(Transcription.is_code_mixed.is_(True)).count()

    lang_rows = q.with_entities(Transcription.detected_languages).all()
    langs = set()
    for (value,) in lang_rows:
        for code in (value or []):
            langs.add(code)

    week_ago = datetime.now(timezone.utc) - timedelta(days=7)
    words_week = db.query(func.coalesce(func.sum(Transcription.word_count), 0)).filter(
        Transcription.user_id == user_id,
        Transcription.deleted_at.is_(None),
        Transcription.created_at >= week_ago,
    ).scalar()

    # correction rate = corrections / words, only when corrections exist
    corrections = db.query(UserCorrection).filter(UserCorrection.user_id == user_id).count()
    correction_rate = round(corrections / words, 4) if words else None

    # streak: consecutive days (ending today or yesterday) with activity
    days = {
        d.date()
        for (d,) in q.with_entities(Transcription.created_at).all()
        if d is not None
    }
    streak = 0
    cursor = datetime.now(timezone.utc).date()
    if cursor not in days and (cursor - timedelta(days=1)) in days:
        cursor -= timedelta(days=1)
    while cursor in days:
        streak += 1
        cursor -= timedelta(days=1)

    return {
        "total_transcriptions": total,
        "total_words": int(words or 0),
        "total_duration_seconds": round(float(duration or 0), 1),
        "code_mixed_percentage": round(100.0 * mixed / total, 1),
        "average_correction_rate": correction_rate,
        "languages_used": len(langs),
        "current_streak_days": streak,
        "words_this_week": int(words_week or 0),
        "has_data": True,
    }


def language_usage(db: Session, user_id: str) -> List[dict]:
    rows = _base_query(db, user_id).with_entities(
        Transcription.detected_languages, Transcription.word_count
    ).all()
    counts: Dict[str, int] = {}
    words: Dict[str, int] = {}
    total_mentions = 0
    for langs, wc in rows:
        for code in (langs or []):
            counts[code] = counts.get(code, 0) + 1
            words[code] = words.get(code, 0) + int(wc or 0)
            total_mentions += 1
    out = [
        {
            "code": code,
            "name": LANGUAGE_NAMES.get(code, code),
            "count": count,
            "words": words.get(code, 0),
            "share": round(count / total_mentions, 3) if total_mentions else 0.0,
        }
        for code, count in sorted(counts.items(), key=lambda kv: -kv[1])
    ]
    return out


def performance(db: Session, user_id: str) -> dict:
    q = _base_query(db, user_id)
    total = q.count()
    latencies = [r[0] for r in q.with_entities(Transcription.latency_ms).all() if r[0] is not None]
    models: Dict[str, int] = {}
    for (m,) in q.with_entities(Transcription.model_used).all():
        if m:
            models[m] = models.get(m, 0) + 1
    statuses: Dict[str, int] = {}
    for (s,) in q.with_entities(Transcription.engine_status).all():
        statuses[s or "unknown"] = statuses.get(s or "unknown", 0) + 1
    with_conf = q.filter(Transcription.confidence.isnot(None)).count()

    latencies.sort()
    p95 = latencies[int(0.95 * (len(latencies) - 1))] if latencies else None

    notes = []
    if total == 0:
        notes.append("No transcriptions yet - metrics appear after your first recording.")
    if with_conf < total:
        notes.append(
            f"Confidence available for {with_conf}/{total} transcriptions. Saaras does not return "
            "token confidence; the rest use our labelled proxy estimate."
        )
    notes.append("WER/CER are not shown here: they require reference transcripts. "
                 "Run the evaluation harness to measure them.")

    return {
        "average_latency_ms": round(sum(latencies) / len(latencies), 1) if latencies else None,
        "p95_latency_ms": round(p95, 1) if p95 is not None else None,
        "model_usage": models,
        "engine_status_breakdown": statuses,
        "confidence_coverage": round(with_conf / total, 3) if total else 0.0,
        "notes": notes,
    }


def weekly_activity(db: Session, user_id: str, weeks: int = 8) -> List[dict]:
    since = datetime.now(timezone.utc) - timedelta(weeks=weeks)
    rows = _base_query(db, user_id).filter(Transcription.created_at >= since).with_entities(
        Transcription.created_at, Transcription.word_count
    ).all()
    buckets: Dict[str, dict] = {}
    for created, wc in rows:
        if created is None:
            continue
        key = created.strftime("%Y-W%V")
        b = buckets.setdefault(key, {"week": key, "transcriptions": 0, "words": 0})
        b["transcriptions"] += 1
        b["words"] += int(wc or 0)
    return sorted(buckets.values(), key=lambda b: b["week"])


def daily_activity(db: Session, user_id: str, days: int = 14) -> List[dict]:
    since = datetime.now(timezone.utc) - timedelta(days=days)
    rows = _base_query(db, user_id).filter(Transcription.created_at >= since).with_entities(
        Transcription.created_at, Transcription.word_count
    ).all()
    buckets: Dict[str, dict] = {}
    for i in range(days):
        d = (datetime.now(timezone.utc) - timedelta(days=days - 1 - i)).strftime("%Y-%m-%d")
        buckets[d] = {"date": d, "transcriptions": 0, "words": 0}
    for created, wc in rows:
        if created is None:
            continue
        key = created.strftime("%Y-%m-%d")
        if key in buckets:
            buckets[key]["transcriptions"] += 1
            buckets[key]["words"] += int(wc or 0)
    return list(buckets.values())
