"""Relay between the browser and Sarvam's realtime WebSocket.

Endpoint: ``wss://api.sarvam.ai/speech-to-text-realtime/ws``
Auth:     ``api-subscription-key`` header
Query:    language_code=auto|xx-IN, stream_type=fast|balanced|simulataneous,
          mode=transcribe|..., endpointing=vad|manual, encoding=linear16,
          sample_rate=16000

Client -> Sarvam: ``{"event": "audio_input", "audio": "<base64 pcm16>"}``
Sarvam -> Client: ``transcript.partial`` / ``transcript.final`` / ``vad.speech_start``
                  / ``vad.speech_end`` / ``session.begin`` / ``error``

The browser never sees the API key: it talks to our FastAPI socket, which opens
the upstream socket with the key and pipes frames both ways.
"""
from __future__ import annotations

import base64
import json
from typing import Any, Callable, Awaitable, Optional

import websockets
from websockets.exceptions import ConnectionClosed

from app.config import settings
from app.core.logging import get_logger

log = get_logger("ai_engine.sarvam.streaming")


class SarvamRealtimeSession:
    def __init__(
        self,
        *,
        mode: str = "transcribe",
        language_code: str = "auto",
        stream_type: str = "balanced",
        sample_rate: int = 16000,
        endpointing: str = "vad",
    ) -> None:
        self.mode = mode
        self.language_code = language_code
        self.stream_type = stream_type
        self.sample_rate = sample_rate
        self.endpointing = endpointing
        self._ws: Optional[Any] = None

    def url(self) -> str:
        q = (
            f"?language_code={self.language_code}"
            f"&stream_type={self.stream_type}"
            f"&mode={self.mode}"
            f"&endpointing={self.endpointing}"
            f"&encoding=linear16"
            f"&sample_rate={self.sample_rate}"
        )
        return settings.sarvam_realtime_ws_url + q

    async def connect(self) -> None:
        if not settings.sarvam_configured:
            raise RuntimeError("SARVAM_API_KEY not configured")
        self._ws = await websockets.connect(
            self.url(),
            additional_headers={"api-subscription-key": settings.sarvam_api_key or ""},
            max_size=8 * 1024 * 1024,
            ping_interval=20,
            ping_timeout=20,
        )
        log.info("sarvam realtime session opened (mode=%s)", self.mode)

    async def send_audio(self, pcm_bytes: bytes) -> None:
        if not self._ws:
            raise RuntimeError("session not connected")
        await self._ws.send(
            json.dumps({"event": "audio_input", "audio": base64.b64encode(pcm_bytes).decode("ascii")})
        )

    async def flush(self) -> None:
        if self._ws:
            await self._ws.send(json.dumps({"event": "flush"}))

    async def close(self) -> None:
        if self._ws:
            try:
                await self._ws.send(json.dumps({"event": "end_session"}))
            except Exception:  # noqa: BLE001 - closing anyway
                pass
            await self._ws.close()
            self._ws = None

    async def pump(
        self,
        on_event: Callable[[dict], Awaitable[None]],
    ) -> None:
        """Forward upstream events to the client callback until the socket closes."""
        if not self._ws:
            raise RuntimeError("session not connected")
        try:
            async for raw in self._ws:
                try:
                    event = json.loads(raw)
                except json.JSONDecodeError:
                    continue
                await on_event(event)
        except ConnectionClosed:
            log.info("sarvam realtime session closed")
