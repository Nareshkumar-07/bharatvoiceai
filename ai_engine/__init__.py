"""BharatVoice AI engine.

Provider-agnostic speech recognition plus the custom intelligence layer:
adaptive routing, code-switch detection, confidence calibration, vocabulary
adaptation and evaluation.  Nothing here imports FastAPI or the database, so the
engine can be unit-tested and reused by the desktop app or a CLI.
"""
from ai_engine.base import (  # noqa: F401
    ASRAdapter,
    ASRResult,
    AdapterError,
    AdapterUnavailable,
    AudioPayload,
    SegmentResult,
    WordToken,
)

__version__ = "1.0.0"
