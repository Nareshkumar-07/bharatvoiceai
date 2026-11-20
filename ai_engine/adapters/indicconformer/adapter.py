"""AI4Bharat IndicConformer adapter (optional, local).

IndicConformer is a CTC conformer trained per-language on Indic data.  It needs
NeMo plus downloaded checkpoints, so it is disabled by default and reports a
precise reason when it cannot run - it never pretends to have transcribed.

Setup (see docs/model_setup.md):
    pip install nemo_toolkit['asr']
    bash scripts/download_models.sh indicconformer
    INDICCONFORMER_ENABLED=true
"""
from __future__ import annotations

import asyncio
from pathlib import Path
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

log = get_logger("ai_engine.indicconformer")

INDIC_CONFORMER_LANGS = {
    "hi-IN": "hi", "bn-IN": "bn", "ta-IN": "ta", "te-IN": "te", "gu-IN": "gu",
    "kn-IN": "kn", "ml-IN": "ml", "mr-IN": "mr", "pa-IN": "pa", "or-IN": "or",
    "as-IN": "as", "ur-IN": "ur",
}


class IndicConformerAdapter(ASRAdapter):
    model_id = "indicconformer"
    provider = "ai4bharat"
    supports_modes = ("transcribe",)
    returns_confidence = False
    supports_streaming = True
    is_remote = False

    def __init__(self, model_dir: Optional[str] = None, enabled: Optional[bool] = None) -> None:
        self.model_dir = Path(model_dir or settings.indicconformer_model_dir)
        self.enabled = settings.indicconformer_enabled if enabled is None else enabled
        self._models: dict[str, Any] = {}
        self._reason: Optional[str] = None

    def _check(self) -> tuple[bool, Optional[str]]:
        if not self.enabled:
            return False, "INDICCONFORMER_ENABLED=false"
        if not self.model_dir.exists():
            return False, f"model directory not found: {self.model_dir}"
        try:
            import nemo.collections.asr as nemo_asr  # type: ignore  # noqa: F401
        except Exception:  # noqa: BLE001
            return False, "nemo_toolkit not installed (pip install 'nemo_toolkit[asr]')"
        return True, None

    async def is_available(self) -> tuple[bool, Optional[str]]:
        return self._check()

    def _load_lang(self, lang2: str) -> Any:
        if lang2 in self._models:
            return self._models[lang2]
        import nemo.collections.asr as nemo_asr  # type: ignore

        ckpt = self.model_dir / f"indicconformer_{lang2}.nemo"
        if not ckpt.exists():
            raise AdapterUnavailable(self.model_id, f"checkpoint missing: {ckpt.name}")
        model = nemo_asr.models.ASRModel.restore_from(str(ckpt))
        model.eval()
        self._models[lang2] = model
        return model

    def _run(self, audio: AudioPayload, language_code: Optional[str]) -> ASRResult:
        lang2 = INDIC_CONFORMER_LANGS.get(language_code or "")
        if not lang2:
            raise AdapterError(
                self.model_id,
                f"language '{language_code}' not supported by IndicConformer; "
                "pass an explicit Indic language_code",
                status_code=400,
            )
        model = self._load_lang(lang2)
        with Timer() as t:
            wav = audio.to_float32()[None, :]
            out = model.transcribe([wav], batch_size=1, logprob=False)
        text = out[0] if isinstance(out, (list, tuple)) else str(out)
        return ASRResult(
            text=text.strip(),
            provider=self.provider,
            model=f"indicconformer-{lang2}",
            mode="transcribe",
            language=language_code,
            segments=[SegmentResult(text=text.strip(), language=language_code,
                                    words=[WordToken(text=w) for w in text.split()])],
            confidence=None,
            confidence_source=None,
            latency_ms=t.elapsed_ms,
        )

    async def transcribe(self, audio: AudioPayload, *, mode: str = "transcribe",
                         language_code: Optional[str] = None, keyterms: Optional[List[str]] = None,
                         context: Optional[str] = None) -> ASRResult:
        ok, reason = self._check()
        if not ok:
            raise AdapterUnavailable(self.model_id, reason or "unavailable")
        if mode != "transcribe":
            raise AdapterError(self.model_id, f"mode '{mode}' unsupported", status_code=400)
        try:
            return await asyncio.to_thread(self._run, audio, language_code)
        except (AdapterUnavailable, AdapterError):
            raise
        except Exception as exc:  # noqa: BLE001
            raise AdapterError(self.model_id, f"inference failed: {exc}") from exc
