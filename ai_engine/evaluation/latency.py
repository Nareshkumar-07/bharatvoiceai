"""Latency recording and percentile reporting."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List

import numpy as np


@dataclass
class LatencyRecorder:
    samples: List[float] = field(default_factory=list)

    def add(self, ms: float) -> None:
        self.samples.append(float(ms))

    def summary(self) -> dict:
        if not self.samples:
            return {"count": 0, "p50_ms": None, "p95_ms": None, "mean_ms": None, "max_ms": None}
        arr = np.asarray(self.samples, dtype=float)
        return {
            "count": int(arr.size),
            "p50_ms": round(float(np.percentile(arr, 50)), 1),
            "p95_ms": round(float(np.percentile(arr, 95)), 1),
            "mean_ms": round(float(arr.mean()), 1),
            "max_ms": round(float(arr.max()), 1),
        }

    def real_time_factor(self, audio_seconds: float) -> float | None:
        if not self.samples or audio_seconds <= 0:
            return None
        return round((sum(self.samples) / 1000.0) / audio_seconds, 4)
