"""Translation: speech->English (Saaras mode) and text->text (Mayura/IndicTrans2).

Two genuinely different operations, kept separate:

* **Speech translation** is done by the ASR provider itself
  (``mode="translate"`` on Saaras) - it translates the audio directly.
* **Text translation** uses ``POST /translate`` (``mayura:v1`` or
  ``sarvam-translate:v1``) or a local IndicTrans2 checkpoint.

Nothing here fabricates a translation: if no backend is configured the caller
gets ``available=False`` with a reason, and the UI shows "translation
unavailable" rather than passing the original text off as a translation.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

import httpx

from app.config import settings
from app.core.logging import get_logger

log = get_logger("ai_engine.translation")

# Sarvam text APIs use od-IN for Odia; the STT endpoint uses or-IN.
TEXT_API_CODE = {"or-IN": "od-IN"}

MAYURA_LANGS = {"bn-IN", "en-IN", "gu-IN", "hi-IN", "kn-IN", "ml-IN", "mr-IN",
                "od-IN", "pa-IN", "ta-IN", "te-IN"}


@dataclass
class TranslationResult:
    text: str
    provider: str
    method: str
    source_language: Optional[str] = None
    target_language: str = "en-IN"
    available: bool = True
    reason: Optional[str] = None
    latency_ms: float = 0.0
    raw: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "text": self.text,
            "provider": self.provider,
            "method": self.method,
            "source_language": self.source_language,
            "target_language": self.target_language,
            "available": self.available,
            "reason": self.reason,
            "latency_ms": round(self.latency_ms, 1),
        }


def _code(code: Optional[str]) -> Optional[str]:
    return TEXT_API_CODE.get(code or "", code) if code else None


class SarvamTranslator:
    """POST /translate with the documented request shape."""

    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None,
                 model: str = "mayura:v1", transport: Optional[httpx.AsyncBaseTransport] = None) -> None:
        self.api_key = api_key if api_key is not None else settings.sarvam_api_key
        self.base_url = (base_url or settings.sarvam_base_url).rstrip("/")
        self.model = model
        self._transport = transport

    async def translate(self, text: str, source: Optional[str], target: str,
                        mode: str = "formal") -> TranslationResult:
        import time

        if not self.api_key:
            return TranslationResult("", "sarvam", "text_api", source, target,
                                     available=False, reason="SARVAM_API_KEY not set")
        src = _code(source) or "auto"
        tgt = _code(target) or "en-IN"
        if src == tgt:
            return TranslationResult(text, "none", "passthrough", src, tgt,
                                     reason="source and target are the same language")
        # Mayura caps input at 1000 chars; chunk long text on sentence boundaries
        chunks = _chunk(text, 900 if self.model == "mayura:v1" else 1800)
        out: List[str] = []
        t0 = time.perf_counter()
        async with httpx.AsyncClient(base_url=self.base_url, timeout=45.0,
                                     transport=self._transport) as client:
            for chunk in chunks:
                body = {
                    "input": chunk,
                    "source_language_code": src,
                    "target_language_code": tgt,
                    "model": self.model,
                }
                if self.model == "mayura:v1":
                    body["mode"] = mode
                resp = await client.post(
                    "/translate", json=body,
                    headers={"api-subscription-key": self.api_key},
                )
                if resp.status_code != 200:
                    return TranslationResult("", "sarvam", "text_api", source, target,
                                             available=False,
                                             reason=f"provider {resp.status_code}: {resp.text[:200]}")
                out.append(resp.json().get("translated_text", ""))
        return TranslationResult(
            text=" ".join(o for o in out if o).strip(),
            provider="sarvam", method=f"text_api:{self.model}",
            source_language=source, target_language=target,
            latency_ms=(time.perf_counter() - t0) * 1000,
        )


class IndicTrans2Translator:
    """Local AI4Bharat IndicTrans2. Real when the checkpoint and deps exist."""

    def __init__(self, model_dir: Optional[str] = None, enabled: Optional[bool] = None) -> None:
        self.model_dir = model_dir or settings.indictrans2_model_dir
        self.enabled = settings.indictrans2_enabled if enabled is None else enabled
        self._pipeline = None

    def available(self) -> tuple[bool, Optional[str]]:
        if not self.enabled:
            return False, "INDICTRANS2_ENABLED=false"
        try:
            import torch  # noqa: F401
            import transformers  # noqa: F401
        except Exception:
            return False, "transformers/torch not installed"
        return True, None

    def translate(self, text: str, source: Optional[str], target: str) -> TranslationResult:
        ok, reason = self.available()
        if not ok:
            return TranslationResult("", "indictrans2", "local", source, target,
                                     available=False, reason=reason)
        import time
        from transformers import AutoModelForSeq2SeqLM, AutoTokenizer  # type: ignore

        t0 = time.perf_counter()
        if self._pipeline is None:
            tok = AutoTokenizer.from_pretrained(self.model_dir, trust_remote_code=True)
            mdl = AutoModelForSeq2SeqLM.from_pretrained(self.model_dir, trust_remote_code=True)
            self._pipeline = (tok, mdl)
        tok, mdl = self._pipeline
        src_tag = f"{source or 'eng_Latn'}" if "Latn" in (source or "") else f"{(source or 'hin')[:3]}"
        tgt_tag = target
        inputs = tok(text, return_tensors="pt", padding=True, truncation=True)
        generated = mdl.generate(**inputs, num_beams=5, max_length=256)
        out = tok.batch_decode(generated, skip_special_tokens=True)[0]
        return TranslationResult(
            text=out, provider="ai4bharat", method="indictrans2_local",
            source_language=src_tag, target_language=tgt_tag,
            latency_ms=(time.perf_counter() - t0) * 1000,
        )


def _chunk(text: str, size: int) -> List[str]:
    if len(text) <= size:
        return [text]
    chunks, current = [], ""
    for sentence in text.replace("?", "?|").replace("!", "!|").replace(".", ".|").split("|"):
        if len(current) + len(sentence) <= size:
            current += sentence
        else:
            if current:
                chunks.append(current)
            current = sentence
    if current:
        chunks.append(current)
    return chunks or [text[:size]]


class TranslationService:
    """Tries the local model first (privacy), then the API."""

    def __init__(self) -> None:
        self.local = IndicTrans2Translator()
        self.api = SarvamTranslator()

    async def translate(self, text: str, source: Optional[str] = None,
                        target: str = "en-IN", mode: str = "formal") -> TranslationResult:
        if not text.strip():
            return TranslationResult("", "none", "noop", source, target, reason="empty input")
        if self.local.available()[0]:
            return self.local.translate(text, source, target)
        return await self.api.translate(text, source, target, mode)

    def status(self) -> dict:
        ok, reason = self.local.available()
        return {
            "local_indictrans2": {"available": ok, "reason": reason},
            "sarvam_text_api": {"available": bool(settings.sarvam_api_key),
                                "reason": None if settings.sarvam_api_key else "SARVAM_API_KEY not set"},
        }


translation_service = TranslationService()
