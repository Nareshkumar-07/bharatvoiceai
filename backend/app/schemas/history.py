from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict


class SegmentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    index: int
    text: str
    language: Optional[str] = None
    language_label: Optional[str] = None
    start_ms: int = 0
    end_ms: int = 0
    confidence: Optional[float] = None
    confidence_source: Optional[str] = None
    is_uncertain: bool = False


class TranscriptionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    title: str
    original_text: str
    native_text: Optional[str] = None
    romanized_text: Optional[str] = None
    english_text: Optional[str] = None
    professional_text: Optional[str] = None
    detected_languages: List[str] = []
    primary_language: Optional[str] = None
    is_code_mixed: bool = False
    code_switch_count: int = 0
    duration_seconds: float = 0.0
    word_count: int = 0
    model_used: Optional[str] = None
    output_mode: str = "transcribe"
    context_profile: str = "general"
    status: str = "completed"
    engine_status: str = "ok"
    confidence: Optional[float] = None
    confidence_source: Optional[str] = None
    latency_ms: Optional[float] = None
    audio_retained: bool = False
    edit_count: int = 0
    created_at: Optional[datetime] = None
    segments: List[SegmentOut] = []


class TranscriptionUpdate(BaseModel):
    title: Optional[str] = None
    original_text: Optional[str] = None
    native_text: Optional[str] = None
    romanized_text: Optional[str] = None
    english_text: Optional[str] = None
    professional_text: Optional[str] = None


class HistoryPage(BaseModel):
    items: List[TranscriptionOut]
    total: int
    page: int
    page_size: int
    pages: int
