"""Transliteration (script conversion, meaning preserved).

Order of preference:
1. Sarvam ``POST /transliterate`` - best quality, needs the key.
2. ``indic-transliteration`` package (offline, deterministic, no model download).
3. Unavailable - reported honestly, never faked with the original text.
"""
from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Optional

import httpx

from ai_engine.multilingual.translation import TEXT_API_CODE
from app.config import settings
from app.core.logging import get_logger

log = get_logger("ai_engine.transliteration")


@dataclass
class TransliterationResult:
    text: str
    provider: str
    method: str
    source_language: Optional[str] = None
    target_language: str = "en-IN"
    available: bool = True
    reason: Optional[str] = None
    latency_ms: float = 0.0

    def to_dict(self) -> dict:
        return {
            "text": self.text, "provider": self.provider, "method": self.method,
            "source_language": self.source_language, "target_language": self.target_language,
            "available": self.available, "reason": self.reason,
            "latency_ms": round(self.latency_ms, 1),
        }


ISO2_FOR_INDIC = {
    "ta-IN": "tamil", "hi-IN": "devanagari", "te-IN": "telugu", "kn-IN": "kannada",
    "ml-IN": "malayalam", "bn-IN": "bengali", "gu-IN": "gujarati", "pa-IN": "gurmukhi",
    "or-IN": "oriya", "mr-IN": "devanagari", "as-IN": "bengali", "ur-IN": "urdu",
}


class TransliterationService:
    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None,
                 transport: Optional[httpx.AsyncBaseTransport] = None) -> None:
        self.api_key = api_key if api_key is not None else settings.sarvam_api_key
        self.base_url = (base_url or settings.sarvam_base_url).rstrip("/")
        self._transport = transport

    def _offline(self, text: str, source: str, target: str) -> TransliterationResult:
        try:
            from indic_transliteration import sanscript  # type: ignore
            from indic_transliteration.sanscript import transliterate  # type: ignore
        except Exception:
            return TransliterationResult(
                "", "none", "unavailable", source, target, available=False,
                reason="no transliteration backend (set SARVAM_API_KEY or pip install indic-transliteration)",
            )
        src_scheme = ISO2_FOR_INDIC.get(source)
        tgt_scheme = ISO2_FOR_INDIC.get(target) or sanscript.ITRANS
        if not src_scheme:
            return TransliterationResult("", "none", "unavailable", source, target,
                                         available=False, reason=f"unsupported source '{source}'")
        t0 = time.perf_counter()
        try:
            out = transliterate(text, getattr(sanscript, src_scheme.upper()), getattr(sanscript, tgt_scheme.upper()))
        except Exception as exc:  # noqa: BLE001
            return TransliterationResult("", "indic-transliteration", "offline", source, target,
                                         available=False, reason=str(exc))
        return TransliterationResult(out, "indic-transliteration", "offline_rulebased", source, target,
                                     latency_ms=(time.perf_counter() - t0) * 1000)

    async def transliterate(self, text: str, source: Optional[str] = "ta-IN",
                            target: str = "en-IN") -> TransliterationResult:
        if not text.strip():
            return TransliterationResult("", "none", "noop", source, target, reason="empty input")
        src = TEXT_API_CODE.get(source or "", source)
        tgt = TEXT_API_CODE.get(target, target)
        if src == tgt:
            return TransliterationResult(text, "none", "passthrough", source, target)

        if self.api_key:
            t0 = time.perf_counter()
            async with httpx.AsyncClient(base_url=self.base_url, timeout=30.0,
                                         transport=self._transport) as client:
                resp = await client.post(
                    "/transliterate",
                    json={"input": text, "source_language_code": src or "auto",
                          "target_language_code": tgt},
                    headers={"api-subscription-key": self.api_key},
                )
            if resp.status_code == 200:
                return TransliterationResult(
                    resp.json().get("transliterated_text", ""),
                    "sarvam", "text_api", source, target,
                    latency_ms=(time.perf_counter() - t0) * 1000,
                )
            log.warning("sarvam transliterate failed: %s %s", resp.status_code, resp.text[:200])

        return self._offline(text, source or "ta-IN", target)

    def status(self) -> dict:
        offline_ok = True
        try:
            import indic_transliteration  # noqa: F401
        except Exception:
            offline_ok = False
        return {
            "sarvam_text_api": {"available": bool(self.api_key),
                                "reason": None if self.api_key else "SARVAM_API_KEY not set"},
            "offline_indic_transliteration": {
                "available": offline_ok,
                "reason": None if offline_ok else "pip install indic-transliteration",
            },
        }


transliteration_service = TransliterationService()
