from __future__ import annotations

from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class ModelInfo(BaseModel):
    model_id: str
    provider: str
    available: bool
    reason: Optional[str] = None
    supports_modes: List[str] = []
    supports_streaming: bool = False
    returns_confidence: bool = False
    runtime: str = "local"
    is_primary: bool = False


class StatusResponse(BaseModel):
    primary_engine: Optional[str]
    primary_available: bool
    streaming_available: bool
    demo_mode: bool
    models: List[ModelInfo]
    translation: dict
    transliteration: dict
    usage: dict
    capabilities: dict
    notes: List[str] = []


class RouterMetrics(BaseModel):
    decisions: int
    escalations: int
    escalation_rate: Optional[float]
    confirmation_requests: int
    average_latency_ms: Optional[float]
    model_usage: Dict[str, int]
    policy: dict
    calibration: dict
    has_data: bool


class RouterPolicyIn(BaseModel):
    enabled: Optional[bool] = None
    confidence_threshold: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    confirmation_threshold: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    max_alternatives: Optional[int] = Field(default=None, ge=0, le=3)
    latency_budget_ms: Optional[float] = Field(default=None, ge=100, le=60000)


class EvaluationResponse(BaseModel):
    available: bool
    reason: Optional[str] = None
    report: Optional[dict] = None
    wer: Optional[float] = None
    cer: Optional[float] = None
    rows: List[dict] = []
    notes: List[str] = []
