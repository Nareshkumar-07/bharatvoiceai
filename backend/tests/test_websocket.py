"""Live dictation socket: protocol, auth, buffering, finalisation."""
from __future__ import annotations

import json

import pytest

from tests.helpers import pcm16


def test_websocket_requires_valid_token(client):
    with pytest.raises(Exception):
        with client.websocket_connect("/ws/speech/live?token=invalid") as ws:
            ws.receive_json()


def test_live_session_streams_audio_and_finalises(client, auth):
    token = auth["token"]
    with client.websocket_connect(f"/ws/speech/live?token={token}") as ws:
        ws.send_json({
            "type": "start",
            "mode": "transcribe",
            "context": "general",
            "language_code": "auto",
            "include_outputs": ["native"],
            "streaming": False,  # no upstream key in tests
            "sample_rate": 16000,
        })
        ready = ws.receive_json()
        assert ready["type"] == "ready"
        assert ready["upstream"] is False
        assert ready["sample_rate"] == 16000

        # one second of PCM in two frames
        data = pcm16(1.0)
        ws.send_bytes(data[: len(data) // 2])
        ws.send_bytes(data[len(data) // 2 :])

        ws.send_json({"type": "stop"})
        message = ws.receive_json()
        # a notice about missing upstream may arrive first
        while message["type"] == "notice":
            message = ws.receive_json()

        assert message["type"] == "final", message
        transcription = message["transcription"]
        assert transcription["engine_status"] == "demo_fixture"
        assert transcription["word_count"] > 0
        assert transcription["id"]


def test_live_session_cancel(client, auth):
    with client.websocket_connect(f"/ws/speech/live?token={auth['token']}") as ws:
        ws.send_json({"type": "start", "mode": "transcribe", "streaming": False})
        ws.receive_json()  # ready
        ws.send_bytes(pcm16(0.3))
        ws.send_json({"type": "cancel"})
        msg = ws.receive_json()
        while msg["type"] == "notice":
            msg = ws.receive_json()
        assert msg["type"] == "cancelled"


def test_ping_pong(client, auth):
    with client.websocket_connect(f"/ws/speech/live?token={auth['token']}") as ws:
        ws.send_json({"type": "start", "mode": "transcribe", "streaming": False})
        ws.receive_json()
        ws.send_json({"type": "ping"})
        assert ws.receive_json()["type"] == "pong"


def test_stop_without_audio_reports_error(client, auth):
    with client.websocket_connect(f"/ws/speech/live?token={auth['token']}") as ws:
        ws.send_json({"type": "start", "mode": "transcribe", "streaming": False})
        ws.receive_json()
        ws.send_json({"type": "stop"})
        msg = ws.receive_json()
        while msg["type"] == "notice":
            msg = ws.receive_json()
        assert msg["type"] == "error"
