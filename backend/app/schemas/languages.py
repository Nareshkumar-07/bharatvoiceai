from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


class LanguageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    code: str
    name: str
    native_name: str
    script: str
    recognition_supported: bool
    is_active: bool = True


class DetectRequest(BaseModel):
    text: str = Field(min_length=1, max_length=5000)
    base_language: Optional[str] = None


class DetectResponse(BaseModel):
    verdict: dict
    code_switching: dict


class TranslateRequest(BaseModel):
    text: str = Field(min_length=1, max_length=5000)
    source_language: Optional[str] = None
    target_language: str = "en-IN"
    mode: str = "formal"


class TranslateResponse(BaseModel):
    text: str
    provider: str
    method: str
    available: bool
    reason: Optional[str] = None
    source_language: Optional[str] = None
    target_language: str
    latency_ms: float = 0.0


class TransliterateRequest(BaseModel):
    text: str = Field(min_length=1, max_length=5000)
    source_language: Optional[str] = "ta-IN"
    target_language: str = "en-IN"


class TransliterateResponse(BaseModel):
    text: str
    provider: str
    method: str
    available: bool
    reason: Optional[str] = None
    latency_ms: float = 0.0
