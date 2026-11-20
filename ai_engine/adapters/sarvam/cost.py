"""Soft usage guard for the Sarvam API.

Sarvam bills per request/second; this meter is a local guard rail, not a
billing system.  It keeps a rolling monthly counter so a runaway loop cannot
silently burn the budget, and exposes numbers for the AI Intelligence screen.
"""
from __future__ import annotations

import threading
from datetime import datetime, timezone
from typing import Dict

from app.config import settings


class UsageMeter:
    def __init__(self, monthly_budget: int | None = None) -> None:
        self.monthly_budget = monthly_budget or settings.sarvam_monthly_request_budget
        self._lock = threading.Lock()
        self._month = self._current_month()
        self._requests = 0
        self._audio_seconds = 0.0
        self._failures = 0

    @staticmethod
    def _current_month() -> str:
        return datetime.now(timezone.utc).strftime("%Y-%m")

    def _roll(self) -> None:
        month = self._current_month()
        if month != self._month:
            self._month, self._requests, self._audio_seconds, self._failures = month, 0, 0.0, 0

    def can_call(self) -> bool:
        with self._lock:
            self._roll()
            return self._requests < self.monthly_budget

    def record(self, audio_seconds: float = 0.0, failed: bool = False) -> None:
        with self._lock:
            self._roll()
            self._requests += 1
            self._audio_seconds += max(0.0, audio_seconds)
            if failed:
                self._failures += 1

    def snapshot(self) -> Dict[str, float | int | str]:
        with self._lock:
            self._roll()
            return {
                "month": self._month,
                "requests": self._requests,
                "monthly_budget": self.monthly_budget,
                "audio_seconds": round(self._audio_seconds, 2),
                "failures": self._failures,
                "utilisation": round(self._requests / self.monthly_budget, 4) if self.monthly_budget else 0.0,
            }


sarvam_usage = UsageMeter()
