"""Seed reference data (languages, model registry) and create tables in dev.

Alembic is the source of truth for schema; this module is used by tests and by
`python -m app.database.init_db` for a zero-friction local start.
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.database.base import Base
from app.database.session import SessionLocal, engine
from app.models import Language, ModelRegistry

LANGUAGES = [
    ("ta-IN", "Tamil", "தமிழ்", "Tamil", True),
    ("hi-IN", "Hindi", "हिन्दी", "Devanagari", True),
    ("te-IN", "Telugu", "తెలుగు", "Telugu", True),
    ("ml-IN", "Malayalam", "മലയാളം", "Malayalam", True),
    ("kn-IN", "Kannada", "ಕನ್ನಡ", "Kannada", True),
    ("bn-IN", "Bengali", "বাংলা", "Bengali", True),
    ("mr-IN", "Marathi", "मराठी", "Devanagari", True),
    ("gu-IN", "Gujarati", "ગુજરાતી", "Gujarati", True),
    ("pa-IN", "Punjabi", "ਪੰਜਾਬੀ", "Gurmukhi", True),
    ("or-IN", "Odia", "ଓଡ଼ିଆ", "Odia", True),
    ("as-IN", "Assamese", "অসমীয়া", "Bengali", True),
    ("ur-IN", "Urdu", "اردو", "Arabic", True),
    ("en-IN", "English", "English", "Latin", True),
]

MODELS = [
    {
        "model_id": "saaras:v4",
        "provider": "sarvam",
        "kind": "asr",
        "display_name": "Sarvam Saaras v4",
        "modes": ["transcribe", "codemix", "translit", "translate", "verbatim"],
        "languages": [c for c, *_ in LANGUAGES],
        "supports_streaming": True,
        "returns_confidence": False,
        "runtime": "remote-api",
        "notes": "Primary recogniser. 23 languages incl. Indian + Global English. No confidence scores returned.",
    },
    {
        "model_id": "whisper",
        "provider": "openai-whisper",
        "kind": "asr",
        "display_name": "Whisper (faster-whisper)",
        "modes": ["transcribe", "translate"],
        "languages": [c for c, *_ in LANGUAGES],
        "supports_streaming": False,
        "returns_confidence": True,
        "runtime": "local",
        "notes": "Fallback / alternative hypothesis source. Needs local model download.",
    },
    {
        "model_id": "indicconformer",
        "provider": "ai4bharat",
        "kind": "asr",
        "display_name": "AI4Bharat IndicConformer",
        "modes": ["transcribe"],
        "languages": [c for c, *_ in LANGUAGES if c != "en-IN"],
        "supports_streaming": True,
        "returns_confidence": False,
        "runtime": "local",
        "notes": "Indic-focused CTC conformer. Needs local weights + NeMo runtime.",
    },
]


def seed_reference_data(db: Session) -> None:
    existing = {c for (c,) in db.query(Language.code).all()}
    for code, name, native, script, supported in LANGUAGES:
        if code not in existing:
            db.add(
                Language(
                    code=code,
                    name=name,
                    native_name=native,
                    script=script,
                    recognition_supported=supported,
                )
            )
    known = {m for (m,) in db.query(ModelRegistry.model_id).all()}
    for m in MODELS:
        if m["model_id"] not in known:
            db.add(ModelRegistry(**m))
    db.commit()


def create_all() -> None:
    from app import models  # noqa: F401  (register mappers)

    Base.metadata.create_all(bind=engine)


if __name__ == "__main__":
    create_all()
    with SessionLocal() as session:
        seed_reference_data(session)
    print("database ready")
