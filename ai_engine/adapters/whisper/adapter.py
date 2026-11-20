"""Whisper adapter (faster-whisper).  Local, optional, real when installed.

Install:
    pip install faster-whisper
    WHISPER_ENABLED=true WHISPER_MODEL=small WHISPER_DEVICE=cpu

faster-whisper exposes per-segment ``avg_logprob``, which is a genuine model
signal.  We convert it to a 0..1 confidence with ``exp(avg_logprob)`` and label
the source ``"provider"`` - it is the model's own number, not our estimate.
"""
from __future__ import annotations

import asyncio
from typing import Any, List, Optional

import numpy as np

from ai_engine.base import (
    ASRAdapter,
    ASRResult,
    AdapterError,
    AdapterUnavailable,
    AudioPayload,
    SegmentResult,
    Timer,
    WordToken,
)
from app.config import settings
from app.core.logging import get_logger

log = get_logger("ai_engine.whisper")


class WhisperAdapter(ASRAdapter):
    model_id = "whisper"
    provider = "openai-whisper"
    supports_modes = ("transcribe", "translate")
    returns_confidence = True
    supports_streaming = False
    is_remote = False

    def __init__(self, model_size: Optional[str] = None, device: Optional[str] = None,
                 compute_type: Optional[str] = None, enabled: Optional[bool] = None) -> None:
        self.model_size = model_size or settings.whisper_model
        self.device = device or settings.whisper_device
        self.compute_type = compute_type or settings.whisper_compute_type
        self.enabled = settings.whisper_enabled if enabled is None else enabled
        self._model: Any = None
        self._import_error: Optional[str] = None

    def _load(self) -> Any:
        if self._model is not None:
            return self._model
        try:
            from faster_whisper import WhisperModel  # type: ignore
        except Exception as exc:  # noqa: BLE001
            self._import_error = f"faster-whisper not installed ({exc.__class__.__name__})"
            raise AdapterUnavailable(self.model_id, self._import_error) from exc
        self._model = WhisperModel(
            self.model_size, device=self.device, compute_type=self.compute_type
        )
        return self._model

    async def is_available(self) -> tuple[bool, Optional[str]]:
        if not self.enabled:
            return False, "WHISPER_ENABLED=false"
        try:
            await asyncio.to_thread(self._load)
        except AdapterUnavailable as exc:
            return False, exc.reason
        except Exception as exc:  # noqa: BLE001 - model download failure etc.
            return False, f"model load failed: {exc}"
        return True, None

    def _run(self, audio: AudioPayload, mode: str, language_code: Optional[str]) -> ASRResult:
        model = self._load()
        with Timer() as t:
            segments, info = model.transcribe(
                audio.to_float32(),
                language=(language_code.split("-")[0] if language_code else None),
                task="translate" if mode == "translate" else "transcribe",
                vad_filter=True,
                beam_size=5,
            )
            out: List[SegmentResult] = []
            for seg in segments:
                conf = float(np.exp(seg.avg_logprob)) if seg.avg_logprob is not None else None
                out.append(
                    SegmentResult(
                        text=seg.text.strip(),
                        start=float(seg.start),
                        end=float(seg.end),
                        language=getattr(info, "language", None),
                        confidence=conf,
                        confidence_source="provider" if conf is not None else None,
                        words=[WordToken(text=w.word.strip()) for w in (seg.words or [])],
                    )
                )
        text = " ".join(s.text for s in out).strip()
        confs = [s.confidence for s in out if s.confidence is not None]
        return ASRResult(
            text=text,
            provider=self.provider,
            model=f"whisper-{self.model_size}",
            mode=mode,
            language=getattr(info, "language", language_code),
            language_probability=float(getattr(info, "language_probability", 0.0) or 0.0) or None,
            segments=out,
            confidence=float(np.mean(confs)) if confs else None,
            confidence_source="provider" if confs else None,
            latency_ms=t.elapsed_ms,
        )

    async def transcribe(self, audio: AudioPayload, *, mode: str = "transcribe",
                         language_code: Optional[str] = None, keyterms: Optional[List[str]] = None,
                         context: Optional[str] = None) -> ASRResult:
        ok, reason = await self.is_available()
        if not ok:
            raise AdapterUnavailable(self.model_id, reason or "unavailable")
        if not audio.data:
            raise AdapterError(self.model_id, "empty audio", status_code=400)
        try:
            return await asyncio.to_thread(self._run, audio, mode, language_code)
        except (AdapterUnavailable, AdapterError):
            raise
        except Exception as exc:  # noqa: BLE001
            raise AdapterError(self.model_id, f"inference failed: {exc}") from exc
