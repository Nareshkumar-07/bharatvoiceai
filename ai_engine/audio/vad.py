"""Voice activity detection.

Default implementation is a small energy + zero-crossing detector that needs no
downloads.  Silero VAD is used instead when installed and enabled - it is better
in noise, but it is an optional dependency and its absence is reported, not
papered over.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

import numpy as np

from ai_engine.base import AudioPayload
from app.config import settings
from app.core.logging import get_logger

log = get_logger("ai_engine.vad")


@dataclass
class VADSegment:
    start: float
    end: float

    def to_dict(self) -> dict:
        return {"start": round(self.start, 3), "end": round(self.end, 3)}


@dataclass
class VADResult:
    segments: List[VADSegment] = field(default_factory=list)
    speech_seconds: float = 0.0
    total_seconds: float = 0.0
    method: str = "energy"
    available: bool = True

    @property
    def speech_ratio(self) -> float:
        return self.speech_seconds / self.total_seconds if self.total_seconds else 0.0

    def to_dict(self) -> dict:
        return {
            "segments": [s.to_dict() for s in self.segments],
            "speech_seconds": round(self.speech_seconds, 3),
            "total_seconds": round(self.total_seconds, 3),
            "speech_ratio": round(self.speech_ratio, 3),
            "method": self.method,
            "available": self.available,
        }


def energy_vad(
    audio: AudioPayload,
    *,
    frame_ms: int = 30,
    threshold_db: float = -38.0,
    min_speech_ms: int = 200,
    min_silence_ms: int = 300,
) -> VADResult:
    """Frame-wise energy VAD with hangover smoothing."""
    if not audio.data:
        return VADResult(total_seconds=audio.duration_seconds, method="energy")
    x = audio.to_float32()
    frame = max(1, int(audio.sample_rate * frame_ms / 1000))
    n = len(x) // frame
    if n == 0:
        return VADResult(total_seconds=audio.duration_seconds, method="energy")

    frames = x[: n * frame].reshape(n, frame)
    rms = np.sqrt(np.mean(frames**2, axis=1) + 1e-12)
    dbfs = 20 * np.log10(rms + 1e-12)
    voiced = dbfs > threshold_db

    # hangover: bridge short gaps
    gap_frames = max(1, min_silence_ms // frame_ms)
    i = 0
    while i < len(voiced):
        if not voiced[i]:
            j = i
            while j < len(voiced) and not voiced[j]:
                j += 1
            if i > 0 and j < len(voiced) and (j - i) < gap_frames:
                voiced[i:j] = True
            i = j
        else:
            i += 1

    segments: List[VADSegment] = []
    min_frames = max(1, min_speech_ms // frame_ms)
    i = 0
    while i < len(voiced):
        if voiced[i]:
            j = i
            while j < len(voiced) and voiced[j]:
                j += 1
            if j - i >= min_frames:
                segments.append(VADSegment(i * frame_ms / 1000.0, j * frame_ms / 1000.0))
            i = j
        else:
            i += 1

    speech = sum(s.end - s.start for s in segments)
    return VADResult(
        segments=segments,
        speech_seconds=speech,
        total_seconds=audio.duration_seconds,
        method="energy",
    )


def silero_vad(audio: AudioPayload) -> Optional[VADResult]:
    """Silero VAD through onnxruntime. Returns None when unavailable."""
    if not settings.silero_vad_enabled:
        return None
    try:
        import onnxruntime  # type: ignore
        from pathlib import Path
    except Exception:
        log.info("silero VAD enabled but onnxruntime is not installed")
        return None
    model_path = Path(settings.silero_vad_model_path)
    if not model_path.exists():
        log.info("silero VAD model missing at %s", model_path)
        return None

    session = onnxruntime.InferenceSession(str(model_path), providers=["CPUExecutionProvider"])
    x = audio.to_float32()
    window = 512  # 16 kHz, 32 ms
    state = np.zeros((2, 1, 128), dtype=np.float32)
    sr = np.array([audio.sample_rate], dtype=np.int64)
    probs = []
    for i in range(0, len(x) - window, window):
        chunk = x[i : i + window].reshape(1, -1)
        out, state = session.run(None, {"input": chunk, "state": state, "sr": sr})
        probs.append(float(out.reshape(-1)[0]))
    if not probs:
        return VADResult(total_seconds=audio.duration_seconds, method="silero", available=True)

    voiced = np.array(probs) > 0.5
    segments: List[VADSegment] = []
    i = 0
    step = window / audio.sample_rate
    while i < len(voiced):
        if voiced[i]:
            j = i
            while j < len(voiced) and voiced[j]:
                j += 1
            segments.append(VADSegment(i * step, j * step))
            i = j
        else:
            i += 1
    speech = sum(s.end - s.start for s in segments)
    return VADResult(segments, speech, audio.duration_seconds, "silero", True)


def detect(audio: AudioPayload) -> VADResult:
    result = silero_vad(audio)
    if result is not None:
        return result
    return energy_vad(audio)
