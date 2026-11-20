from __future__ import annotations

from typing import Dict, List, Optional

from pydantic import BaseModel


class AnalyticsOverview(BaseModel):
    total_transcriptions: int
    total_words: int
    total_duration_seconds: float
    code_mixed_percentage: float
    average_correction_rate: Optional[float]
    languages_used: int
    current_streak_days: int
    words_this_week: int
    has_data: bool = True


class LanguageUsage(BaseModel):
    code: str
    name: str
    count: int
    words: int
    share: float


class PerformanceMetrics(BaseModel):
    average_latency_ms: Optional[float]
    p95_latency_ms: Optional[float]
    model_usage: Dict[str, int]
    engine_status_breakdown: Dict[str, int]
    confidence_coverage: float
    notes: List[str] = []
