"""Live dictation WebSocket.

Protocol (client -> server)
---------------------------
    {"type": "start", "mode": "transcribe", "language_code": "auto",
     "context": "general", "streaming": true, "include_outputs": ["native"]}
    <binary frames: mono 16-bit PCM at the negotiated sample_rate>
    {"type": "stop"} | {"type": "cancel"} | {"type": "ping"}

Server -> client
----------------
    {"type": "ready", "session_id": ..., "upstream": true|false, "engine": {...}}
    {"type": "partial", "text": ...}      # ONLY real upstream partials
    {"type": "final", "transcription": {...}}
    {"type": "notice"|"error", ...}

Honesty rules
-------------
* Partials are forwarded from Sarvam's realtime socket.  If that socket is not
  available we say so and never emit a simulated partial.
* On ``stop`` we persist exactly one transcription.  When the upstream stream
  already produced final text we use it (no duplicate ASR call); otherwise we run
  the router on the buffered audio.
"""
from __future__ import annotations

import asyncio
import json
import uuid
from typing import List, Optional

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, status

from ai_engine.adapters.sarvam.streaming import SarvamRealtimeSession
from ai_engine.base import AdapterError, AdapterUnavailable, AudioPayload
from app.config import settings
from app.core.logging import get_logger
from app.core.security import decode_token
from app.database.session import SessionLocal
from app.models import User
from app.schemas.speech import TranscribeOptions
from app.services.speech_service import persist_streamed, transcribe_audio

router = APIRouter()
log = get_logger("backend.ws")

MAX_BUFFER_BYTES = 16000 * 2 * settings.max_recording_seconds


async def _send(ws: WebSocket, payload: dict) -> None:
    await ws.send_text(json.dumps(payload, ensure_ascii=False))


def _user_from_token(token: str) -> Optional[User]:
    try:
        data = decode_token(token, "access")
    except Exception:  # noqa: BLE001
        return None
    db = SessionLocal()
    try:
        user = db.get(User, data["sub"])
        if user is None or not user.is_active:
            return None
        db.expunge(user)
        return user
    finally:
        db.close()


@router.websocket("/ws/speech/live")
async def live_speech(ws: WebSocket, token: str = "") -> None:
    user = _user_from_token(token)
    if user is None:
        await ws.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    await ws.accept()
    session_id = uuid.uuid4().hex[:12]
    buffer = bytearray()
    sample_rate = 16000
    options = TranscribeOptions()
    upstream: Optional[SarvamRealtimeSession] = None
    pump_task: Optional[asyncio.Task] = None
    upstream_finals: List[str] = []
    upstream_partial = ""
    upstream_language: Optional[str] = None

    async def on_upstream_event(event: dict) -> None:
        nonlocal upstream_partial, upstream_language
        etype = (event.get("type") or event.get("event") or "").lower()
        if "partial" in etype:
            text = event.get("transcript") or event.get("text") or ""
            if text:
                upstream_partial = text
                await _send(ws, {"type": "partial", "text": text})
        elif "final" in etype:
            text = event.get("transcript") or event.get("text") or ""
            if text:
                upstream_finals.append(text)
                upstream_language = event.get("language_code") or upstream_language
                await _send(ws, {"type": "final_segment", "text": text,
                                 "language": upstream_language})
        elif "speech_start" in etype or "speech_end" in etype:
            await _send(ws, {"type": "vad", "event": etype})
        elif etype == "error":
            await _send(ws, {"type": "error", "message": event.get("message", "upstream error"),
                             "fatal": bool(event.get("is_fatal"))})

    try:
        while True:
            message = await ws.receive()
            if message.get("type") == "websocket.disconnect":
                break

            if message.get("bytes") is not None:
                chunk = message["bytes"]
                if len(buffer) + len(chunk) > MAX_BUFFER_BYTES:
                    await _send(ws, {"type": "error", "message": "Maximum recording length reached",
                                     "fatal": True})
                    break
                buffer.extend(chunk)
                if upstream is not None:
                    try:
                        await upstream.send_audio(chunk)
                    except Exception as exc:  # noqa: BLE001
                        log.warning("upstream send failed: %s", exc)
                        upstream = None
                continue

            try:
                payload = json.loads(message.get("text") or "{}")
            except json.JSONDecodeError:
                await _send(ws, {"type": "error", "message": "Malformed JSON control message"})
                continue

            mtype = payload.get("type")

            if mtype == "start":
                options = TranscribeOptions(
                    mode=payload.get("mode", "transcribe"),
                    context=payload.get("context", "general"),
                    language_code=payload.get("language_code") or None,
                    prefer_model=payload.get("prefer_model"),
                    include_outputs=payload.get("include_outputs") or ["native"],
                    noise_reduction=bool(payload.get("noise_reduction")),
                    retain_audio=bool(payload.get("retain_audio")),
                )
                sample_rate = int(payload.get("sample_rate") or 16000)
                buffer.clear()
                upstream_finals.clear()

                want_stream = bool(payload.get("streaming", True))
                if want_stream and settings.sarvam_configured and options.mode in (
                    "transcribe", "codemix", "translit", "translate", "verbatim"
                ):
                    try:
                        upstream = SarvamRealtimeSession(
                            mode=options.mode,
                            language_code=options.language_code or "auto",
                            sample_rate=sample_rate,
                        )
                        await upstream.connect()
                        pump_task = asyncio.create_task(upstream.pump(on_upstream_event))
                    except Exception as exc:  # noqa: BLE001
                        upstream = None
                        await _send(ws, {
                            "type": "notice",
                            "message": f"Realtime upstream unavailable ({exc}). "
                                       "You will get a final transcript after you stop, without partials.",
                        })
                elif want_stream:
                    await _send(ws, {
                        "type": "notice",
                        "message": "Streaming partials need SARVAM_API_KEY on the backend. "
                                   "Recording is still captured and transcribed on stop.",
                    })

                await _send(ws, {
                    "type": "ready",
                    "session_id": session_id,
                    "sample_rate": sample_rate,
                    "upstream": upstream is not None,
                    "engine": {"mode": options.mode, "context": options.context},
                    "demo_mode": settings.demo_mode,
                })

            elif mtype == "stop":
                if upstream is not None:
                    try:
                        await upstream.flush()
                        await asyncio.sleep(0.3)
                    except Exception:  # noqa: BLE001
                        pass
                if pump_task:
                    pump_task.cancel()
                if upstream is not None:
                    await upstream.close()

                audio = AudioPayload(bytes(buffer), sample_rate=sample_rate, channels=1, sample_width=2)
                if not buffer:
                    await _send(ws, {"type": "error", "message": "No audio was received"})
                    continue

                db = SessionLocal()
                try:
                    if upstream_finals:
                        result = await persist_streamed(
                            db, user, text=" ".join(upstream_finals).strip(),
                            language=upstream_language, audio=audio,
                            options=options, model_label=f"{settings.sarvam_model} (realtime)",
                        )
                    else:
                        result = await transcribe_audio(db, user, audio, options)
                except AdapterUnavailable as exc:
                    await _send(ws, {"type": "error", "message": str(exc), "fatal": True})
                    break
                except AdapterError as exc:
                    await _send(ws, {"type": "error", "message": str(exc), "fatal": True})
                    break
                except Exception as exc:  # noqa: BLE001
                    log.exception("finalisation failed")
                    await _send(ws, {"type": "error", "message": f"Could not finalise: {exc}"})
                    break
                finally:
                    db.close()

                await _send(ws, {"type": "final", "transcription": result})
                buffer.clear()
                upstream_finals.clear()

            elif mtype == "cancel":
                if pump_task:
                    pump_task.cancel()
                if upstream is not None:
                    await upstream.close()
                    upstream = None
                buffer.clear()
                upstream_finals.clear()
                await _send(ws, {"type": "cancelled", "session_id": session_id})

            elif mtype == "ping":
                await _send(ws, {"type": "pong"})

    except WebSocketDisconnect:
        log.info("client disconnected from live session %s", session_id)
    finally:
        if pump_task:
            pump_task.cancel()
        if upstream is not None:
            try:
                await upstream.close()
            except Exception:  # noqa: BLE001
                pass
