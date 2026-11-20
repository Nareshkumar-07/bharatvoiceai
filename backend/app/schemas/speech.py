from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field


class TranscribeOptions(BaseModel):
    mode: str = Field(default="transcribe", pattern="^(transcribe|codemix|translit|translate|verbatim)$")
    context: str = Field(default="general", max_length=24)
    language_code: Optional[str] = None
    prefer_model: Optional[str] = None
    include_outputs: List[str] = Field(default_factory=lambda: ["native"])
    noise_reduction: bool = False
    title: Optional[str] = None
    retain_audio: bool = False


class SpeechResult(BaseModel):
    id: str
    text: str
    mode: str
    primary_language: Optional[str] = None
    languages: List[str] = Field(default_factory=list)
    is_code_mixed: bool = False
    code_switch_count: int = 0
    confidence: Optional[float] = None
    confidence_source: Optional[str] = None
    confidence_components: dict = Field(default_factory=dict)
    engine_status: str = "ok"
    demo: bool = False
    model_used: Optional[str] = None
    latency_ms: Optional[float] = None
    needs_confirmation: bool = False
    segments: List[dict] = Field(default_factory=list)
    outputs: dict = Field(default_factory=dict)
    routing: dict = Field(default_factory=dict)
    audio: dict = Field(default_factory=dict)
    word_count: int = 0
    duration_seconds: float = 0.0
    message: Optional[str] = None
