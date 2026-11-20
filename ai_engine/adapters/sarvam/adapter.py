"""Sarvam AI Saaras adapter - the primary recogniser.

Verified against the public API contract:

* REST:  ``POST {base}/speech-to-text`` (multipart ``file``), form fields
  ``model``, ``mode``, ``language_code``, ``keyterms``; header
  ``api-subscription-key``.
* Modes: ``transcribe`` | ``translate`` | ``verbatim`` | ``translit`` | ``codemix``.
* Audio: WAV/MP3/AAC/FLAC/OGG, <= 30 s per REST request (batch API for longer).
* Saaras does **not** return per-word confidence.  This adapter therefore leaves
  ``confidence`` as ``None`` and the calibration layer supplies a labelled proxy.

The API key is read from the backend environment only and is never logged.
"""
from __future__ import annotations

import asyncio
from typing import Any, Dict, List, Optional

import httpx

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

log = get_logger("ai_engine.sarvam")

SARVAM_MODES = ("transcribe", "translate", "verbatim", "translit", "codemix")
# Saaras REST accepts up to 30 s per request.
REST_MAX_SECONDS = 30.0


class SarvamAdapter(ASRAdapter):
    model_id = "saaras:v4"
    provider = "sarvam"
    supports_modes = SARVAM_MODES
    returns_confidence = False
    supports_streaming = True
    is_remote = True

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        stt_path: Optional[str] = None,
        model: Optional[str] = None,
        timeout: Optional[float] = None,
        max_retries: Optional[int] = None,
        transport: Optional[httpx.AsyncBaseTransport] = None,
    ) -> None:
        self.api_key = api_key if api_key is not None else settings.sarvam_api_key
        self.base_url = (base_url or settings.sarvam_base_url).rstrip("/")
        self.stt_path = stt_path or settings.sarvam_stt_path
        self.model = model or settings.sarvam_model
        self.timeout = timeout if timeout is not None else settings.sarvam_timeout_seconds
        self.max_retries = max_retries if max_retries is not None else settings.sarvam_max_retries
        self._transport = transport
        self._client: Optional[httpx.AsyncClient] = None

    # -- lifecycle ---------------------------------------------------------
    def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=httpx.Timeout(self.timeout),
                transport=self._transport,
                headers={"api-subscription-key": self.api_key or ""},
            )
        return self._client

    async def aclose(self) -> None:
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    async def is_available(self) -> tuple[bool, Optional[str]]:
        if not self.api_key or not self.api_key.strip():
            return False, "SARVAM_API_KEY is not set (backend environment variable)"
        return True, None

    # -- request building --------------------------------------------------
    def _form_fields(
        self,
        mode: str,
        language_code: Optional[str],
        keyterms: Optional[List[str]],
    ) -> List[tuple[str, str]]:
        fields: List[tuple[str, str]] = [("model", self.model), ("mode", mode)]
        # "auto" / None means: let Saaras detect the language.
        if language_code and language_code.lower() not in ("auto", "unknown", ""):
            fields.append(("language_code", language_code))
        # keyterm prompting is a saaras:v4 feature, max 50 terms
        for term in (keyterms or [])[:50]:
            if term and term.strip():
                fields.append(("keyterms", term.strip()))
        return fields

    # -- main call ---------------------------------------------------------
    async def transcribe(
        self,
        audio: AudioPayload,
        *,
        mode: str = "transcribe",
        language_code: Optional[str] = None,
        keyterms: Optional[List[str]] = None,
        context: Optional[str] = None,
    ) -> ASRResult:
        ok, reason = await self.is_available()
        if not ok:
            raise AdapterUnavailable(self.model, reason or "not configured")
        if mode not in SARVAM_MODES:
            raise AdapterError(self.model, f"unsupported mode '{mode}'", status_code=400)
        if not audio.data:
            raise AdapterError(self.model, "empty audio buffer", status_code=400)
        if audio.duration_seconds > REST_MAX_SECONDS + 0.5:
            raise AdapterError(
                self.model,
                f"audio is {audio.duration_seconds:.1f}s; the REST endpoint accepts <=30s. "
                "Split into segments (the router does this) or use the batch API.",
                status_code=413,
            )

        wav = audio.to_wav_bytes()
        files = {"file": ("audio.wav", wav, "audio/wav")}
        fields = self._form_fields(mode, language_code, keyterms)

        last_error: Optional[Exception] = None
        for attempt in range(self.max_retries + 1):
            with Timer() as t:
                try:
                    resp = await self._get_client().post(self.stt_path, data=fields, files=files)
                except httpx.HTTPError as exc:  # network / timeout
                    last_error = exc
                    log.warning("sarvam transport error (attempt %s): %s", attempt + 1, exc)
                    if attempt < self.max_retries:
                        await asyncio.sleep(0.6 * (2**attempt))
                        continue
                    raise AdapterError(self.model, f"network error: {exc}", retryable=True) from exc

            if resp.status_code == 200:
                return self._parse(resp.json(), mode, language_code, t.elapsed_ms)

            body = resp.text[:400]
            if resp.status_code in (401, 403):
                raise AdapterError(
                    self.model,
                    "authentication failed - check SARVAM_API_KEY",
                    status_code=502,
                )
            if resp.status_code == 429:
                if attempt < self.max_retries:
                    await asyncio.sleep(1.0 * (2**attempt))
                    last_error = AdapterError(self.model, "rate limited", retryable=True, status_code=429)
                    continue
                raise AdapterError(self.model, "rate limited by provider", retryable=True, status_code=429)
            if resp.status_code >= 500 and attempt < self.max_retries:
                last_error = AdapterError(self.model, f"upstream {resp.status_code}: {body}", retryable=True)
                await asyncio.sleep(0.6 * (2**attempt))
                continue
            raise AdapterError(
                self.model,
                f"provider returned {resp.status_code}: {body}",
                retryable=resp.status_code >= 500,
                status_code=502 if resp.status_code >= 500 else 400,
            )

        raise AdapterError(self.model, f"exhausted retries: {last_error}", retryable=True)

    # -- response parsing --------------------------------------------------
    def _parse(
        self,
        payload: Dict[str, Any],
        mode: str,
        language_code: Optional[str],
        latency_ms: float,
    ) -> ASRResult:
        text = (payload.get("transcript") or "").strip()
        detected = payload.get("language_code") or language_code
        # Saaras returns language_probability on some responses; keep it only if real.
        prob = payload.get("language_probability")
        try:
            prob = float(prob) if prob is not None else None
        except (TypeError, ValueError):
            prob = None

        segments: List[SegmentResult] = []
        for seg in payload.get("diarized_transcript", {}).get("entries", []) or []:
            seg_text = (seg.get("transcript") or "").strip()
            if not seg_text:
                continue
            segments.append(
                SegmentResult(
                    text=seg_text,
                    start=float(seg.get("start_time_seconds") or 0.0),
                    end=float(seg.get("end_time_seconds") or 0.0),
                    language=detected,
                    words=[WordToken(text=w) for w in seg_text.split()],
                )
            )
        if not segments and text:
            segments = [
                SegmentResult(
                    text=text,
                    start=0.0,
                    end=0.0,
                    language=detected,
                    words=[WordToken(text=w) for w in text.split()],
                )
            ]

        return ASRResult(
            text=text,
            provider=self.provider,
            model=self.model,
            mode=mode,
            language=detected,
            language_probability=prob,
            segments=segments,
            confidence=None,          # Saaras gives no token confidence: never invent one
            confidence_source=None,
            latency_ms=latency_ms,
            engine_status="ok",
            raw={"request_id": payload.get("request_id"), "keys": sorted(payload.keys())},
        )
