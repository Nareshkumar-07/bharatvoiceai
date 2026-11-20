#!/usr/bin/env python3
"""Create a demo account with a handful of transcriptions, for UI exploration.

    python scripts/seed_demo.py --email demo@bharatvoice.ai --password demo12345

Rows are inserted with engine_status="demo_fixture" and model "demo-seed" so they
are never mistaken for real recognitions in the UI or in exports.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
for p in (str(REPO_ROOT), str(REPO_ROOT / "backend")):
    if p not in sys.path:
        sys.path.insert(0, p)

from app.core.security import hash_password  # noqa: E402
from app.database.init_db import create_all, seed_reference_data  # noqa: E402
from app.database.session import SessionLocal  # noqa: E402
from app.models import (  # noqa: E402
    AnalyticsEvent,
    Transcription,
    TranscriptionSegment,
    User,
    UserPreference,
    UserVocabulary,
)

SAMPLES = [
    {
        "text": "Bro inniku college ku late ah varuven because traffic romba jasthi",
        "lang": "ta-IN", "languages": ["ta-IN", "en-IN"], "mixed": True, "switches": 4,
        "segments": [("Bro inniku college ku late ah varuven", "ta-IN", "matrix", 0.7),
                     ("because traffic romba jasthi", "ta-IN", "matrix", 0.65)],
    },
    {
        "text": "Kal meeting hai presentation ready karna hai deadline Friday tak",
        "lang": "hi-IN", "languages": ["hi-IN", "en-IN"], "mixed": True, "switches": 3,
        "segments": [("Kal meeting hai", "hi-IN", "matrix", 0.72),
                     ("presentation ready karna hai", "hi-IN", "matrix", 0.7)],
    },
    {
        "text": "Repo ki pull request pampinchu, tests pass ayyayi",
        "lang": "te-IN", "languages": ["te-IN", "en-IN"], "mixed": True, "switches": 2,
        "segments": [("Repo ki pull request pampinchu", "te-IN", "matrix", 0.68)],
    },
    {
        "text": "Submit the report before Friday",
        "lang": "en-IN", "languages": ["en-IN"], "mixed": False, "switches": 0,
        "segments": [("Submit the report before Friday", "en-IN", "matrix", 0.9)],
    },
]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--email", default="demo@bharatvoice.ai")
    parser.add_argument("--password", default="demo12345")
    args = parser.parse_args()

    create_all()
    with SessionLocal() as db:
        seed_reference_data(db)
        user = db.query(User).filter(User.email == args.email.lower()).first()
        if user is None:
            user = User(email=args.email.lower(), hashed_password=hash_password(args.password),
                        full_name="Demo User", is_demo=True)
            db.add(user)
            db.flush()
            db.add(UserPreference(user_id=user.id))
        else:
            print(f"user {args.email} already exists; adding samples anyway")

        for vocab in [
            ("naresh", "Naresh", "personal_name"),
            ("cit", "CIT", "acronym"),
            ("fastapi", "FastAPI", "technical"),
        ]:
            exists = db.query(UserVocabulary).filter(
                UserVocabulary.user_id == user.id, UserVocabulary.word == vocab[0]
            ).first()
            if not exists:
                db.add(UserVocabulary(user_id=user.id, word=vocab[0],
                                      preferred_spelling=vocab[1], category=vocab[2]))

        for i, sample in enumerate(SAMPLES):
            transcription = Transcription(
                user_id=user.id,
                title=sample["text"][:50],
                original_text=sample["text"],
                native_text=sample["text"],
                detected_languages=sample["languages"],
                primary_language=sample["lang"],
                is_code_mixed=sample["mixed"],
                code_switch_count=sample["switches"],
                duration_seconds=3.5 + i,
                word_count=len(sample["text"].split()),
                model_used="demo-seed",
                engine_status="demo_fixture",
                confidence=None,
                confidence_source=None,
                latency_ms=0.0,
            )
            db.add(transcription)
            db.flush()
            for index, (text, lang, kind, conf) in enumerate(sample["segments"]):
                db.add(TranscriptionSegment(
                    transcription_id=transcription.id, index=index, text=text,
                    language=lang, language_label=lang, confidence=conf,
                    confidence_source="heuristic", is_uncertain=kind == "uncertain",
                ))
            db.add(AnalyticsEvent(user_id=user.id, event_type="transcription_completed",
                                  payload={"transcription_id": transcription.id, "demo": True}))
        db.commit()

    print(f"seeded {len(SAMPLES)} demo transcriptions for {args.email} / {args.password}")
    print("NOTE: these rows are marked engine_status=demo_fixture and are badged in the UI.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
