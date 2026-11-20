"""Core contracts shared by every ASR adapter.

Design rules that the rest of the engine relies on:

* An adapter either produces a real transcript or raises.  It never returns
  invented text.
* Confidence is optional and always labelled: ``"provider"`` when the model
  itself reported it, ``"proxy"`` when our calibration layer estimated it,
  ``"heuristic"`` for linguistic heuristics, ``None`` when unknown.
* ``engine_status`` tells the caller what actually happened:
  ``ok`` | ``degraded`` (fallback used) | ``demo_fixture`` | ``unavailable``.
"""
from __future__ import annotations

import io
import time
import uuid
import wave
from abc import ABC, abstractmethod
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Literal, Optional, Sequence

import numpy as np

OutputMode = Literal["transcribe", "codemix", "translit", "translate", "verbatim"]
OUTPUT_MODES: tuple[str, ...] = ("transcribe", "codemix", "translit", "translate", "verbatim")
EngineStatus = Literal["ok", "degraded", "demo_fixture", "unavailable"]
ConfidenceSource = Literal["provider", "proxy", "heuristic"]


# --------------------------------------------------------------------------- #
# Audio
# --------------------------------------------------------------------------- #
@dataclass
class AudioPayload:
    """Mono 16-bit PCM audio, plus everything needed to wrap it as WAV."""

    data: bytes
    sample_rate: int = 16000
    channels: int = 1
    sample_width: int = 2
    encoding: str = "pcm_s16le"
    duration_seconds: float = 0.0

    def __post_init__(self) -> None:
        if not self.duration_seconds and self.data:
            bytes_per_frame = self.sample_width * self.channels
            self.duration_seconds = len(self.data) / float(self.sample_rate * bytes_per_frame)

    # -- helpers -----------------------------------------------------------
    @classmethod
    def from_wav_bytes(cls, raw: bytes) -> "AudioPayload":
        with wave.open(io.BytesIO(raw), "rb") as wf:
            return cls(
                data=wf.readframes(wf.getnframes()),
                sample_rate=wf.getframerate(),
                channels=wf.getnchannels(),
                sample_width=wf.getsampwidth(),
                duration_seconds=wf.getnframes() / float(wf.getframerate() or 1),
            )

    def to_wav_bytes(self) -> bytes:
        buf = io.BytesIO()
        with wave.open(buf, "wb") as wf:
            wf.setnchannels(self.channels)
            wf.setsampwidth(self.sample_width)
            wf.setframerate(self.sample_rate)
            wf.writeframes(self.data)
        return buf.getvalue()

    def to_float32(self) -> np.ndarray:
        if self.sample_width == 2:
            arr = np.frombuffer(self.data, dtype=np.int16).astype(np.float32)
            return arr / 32768.0
        if self.sample_width == 4:
            arr = np.frombuffer(self.data, dtype=np.int32).astype(np.float32)
            return arr / 2147483648.0
        raise ValueError(f"unsupported sample width {self.sample_width}")

    def slice_seconds(self, start: float, end: float) -> "AudioPayload":
        """Slice by time. Used by the router to re-run only uncertain segments."""
        start = max(0.0, start)
        end = min(self.duration_seconds, end)
        if end <= start:
            return AudioPayload(b"", self.sample_rate, self.channels, self.sample_width)
        f0 = int(start * self.sample_rate)
        f1 = int(end * self.sample_rate)
        return AudioPayload(
            data=self.data[f0 * self.sample_width : f1 * self.sample_width],
            sample_rate=self.sample_rate,
            channels=self.channels,
            sample_width=self.sample_width,
        )

    def peak(self) -> float:
        if not self.data:
            return 0.0
        arr = np.abs(self.to_float32())
        return float(arr.max()) if arr.size else 0.0

    def dbfs(self) -> float:
        p = self.peak()
        return 20.0 * float(np.log10(p)) if p > 0 else -120.0


# --------------------------------------------------------------------------- #
# Results
# --------------------------------------------------------------------------- #
@dataclass
class WordToken:
    text: str
    start: Optional[float] = None
    end: Optional[float] = None
    confidence: Optional[float] = None
    language: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class SegmentResult:
    text: str
    start: float = 0.0
    end: float = 0.0
    language: Optional[str] = None
    confidence: Optional[float] = None
    confidence_source: Optional[str] = None
    words: List[WordToken] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["words"] = [w.to_dict() for w in self.words]
        return d


@dataclass
class ASRResult:
    text: str
    provider: str
    model: str
    mode: str = "transcribe"
    language: Optional[str] = None
    language_probability: Optional[float] = None
    segments: List[SegmentResult] = field(default_factory=list)
    confidence: Optional[float] = None
    confidence_source: Optional[str] = None
    latency_ms: float = 0.0
    engine_status: str = "ok"
    demo: bool = False
    raw: Dict[str, Any] = field(default_factory=dict)
    request_id: str = field(default_factory=lambda: uuid.uuid4().hex)

    @property
    def word_count(self) -> int:
        return len(self.text.split())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "text": self.text,
            "provider": self.provider,
            "model": self.model,
            "mode": self.mode,
            "language": self.language,
            "language_probability": self.language_probability,
            "segments": [s.to_dict() for s in self.segments],
            "confidence": self.confidence,
            "confidence_source": self.confidence_source,
            "latency_ms": self.latency_ms,
            "engine_status": self.engine_status,
            "demo": self.demo,
            "request_id": self.request_id,
        }


# --------------------------------------------------------------------------- #
# Errors
# --------------------------------------------------------------------------- #
class AdapterUnavailable(RuntimeError):
    """The adapter cannot run at all (missing key, missing weights, bad config)."""

    def __init__(self, model: str, reason: str) -> None:
        self.model = model
        self.reason = reason
        super().__init__(f"{model} unavailable: {reason}")


class AdapterError(RuntimeError):
    """A run was attempted and failed."""

    def __init__(self, model: str, message: str, *, retryable: bool = False, status_code: int = 502):
        self.model = model
        self.retryable = retryable
        self.status_code = status_code
        super().__init__(f"{model}: {message}")


# --------------------------------------------------------------------------- #
# Adapter contract
# --------------------------------------------------------------------------- #
class ASRAdapter(ABC):
    model_id: str = "abstract"
    provider: str = "abstract"
    supports_modes: Sequence[str] = ("transcribe",)
    returns_confidence: bool = False
    supports_streaming: bool = False
    is_remote: bool = False

    @abstractmethod
    async def is_available(self) -> tuple[bool, Optional[str]]:
        """(available, reason_if_not). Must not raise."""

    @abstractmethod
    async def transcribe(
        self,
        audio: AudioPayload,
        *,
        mode: str = "transcribe",
        language_code: Optional[str] = None,
        keyterms: Optional[List[str]] = None,
        context: Optional[str] = None,
    ) -> ASRResult:
        """Recognise audio. Raises AdapterUnavailable / AdapterError."""

    async def aclose(self) -> None:  # optional cleanup
        return None


class Timer:
    def __enter__(self) -> "Timer":
        self.t0 = time.perf_counter()
        return self

    def __exit__(self, *exc: Any) -> None:
        self.elapsed_ms = (time.perf_counter() - self.t0) * 1000.0
