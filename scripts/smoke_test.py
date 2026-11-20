#!/usr/bin/env python3
"""End-to-end smoke test against a running backend.

    python scripts/smoke_test.py --base http://localhost:8000

Checks: health, register/login, engine status, vocabulary CRUD, a real
transcription request, history, analytics and settings. Prints PASS/FAIL per
step and exits non-zero on failure.
"""
from __future__ import annotations

import argparse
import io
import math
import struct
import sys
import uuid
import wave

import httpx


def make_wav(seconds: float = 1.5, rate: int = 16000) -> bytes:
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(rate)
        frames = bytearray()
        for i in range(int(seconds * rate)):
            frames += struct.pack("<h", int(0.35 * 32767 * math.sin(2 * math.pi * 210 * i / rate)))
        wf.writeframes(bytes(frames))
    return buf.getvalue()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", default="http://localhost:8000")
    args = parser.parse_args()

    client = httpx.Client(base_url=args.base, timeout=60.0)
    failures = 0

    def check(name: str, condition: bool, detail: str = "") -> None:
        nonlocal failures
        status = "PASS" if condition else "FAIL"
        print(f"[{status}] {name}{(' — ' + detail) if detail else ''}")
        if not condition:
            failures += 1

    r = client.get("/health")
    check("health", r.status_code == 200)

    email = f"smoke.{uuid.uuid4().hex[:8]}@example.com"
    r = client.post("/api/auth/register", json={"email": email, "password": "smoketest123", "full_name": "Smoke"})
    check("register", r.status_code == 201, r.text[:120])
    if r.status_code != 201:
        return 1
    token = r.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    check("me", client.get("/api/auth/me", headers=headers).status_code == 200)

    status = client.get("/api/ai/status", headers=headers)
    check("ai status", status.status_code == 200)
    payload = status.json()
    print(f"        primary={payload.get('primary_engine')} available={payload.get('primary_available')}")
    print(f"        demo_mode={payload.get('demo_mode')}")

    r = client.post("/api/vocabulary", headers=headers,
                    json={"word": "naresh", "preferred_spelling": "Naresh", "category": "personal_name"})
    check("vocabulary create", r.status_code == 201, r.text[:120])
    vocab_id = r.json().get("id") if r.status_code == 201 else None

    r = client.post(
        "/api/speech/transcribe",
        headers=headers,
        files={"file": ("smoke.wav", io.BytesIO(make_wav()), "audio/wav")},
        data={"mode": "transcribe", "context": "general", "include_outputs": "native"},
    )
    ok = r.status_code == 200
    check("transcribe", ok, r.text[:200] if not ok else "")
    transcription_id = None
    if ok:
        body = r.json()
        transcription_id = body["id"]
        print(f"        engine_status={body['engine_status']} demo={body['demo']} words={body['word_count']}")
        print(f"        text={body['text'][:80]!r}")
        check("transcription labelled", body["engine_status"] in ("ok", "degraded", "demo_fixture"))

    if transcription_id:
        check("history detail", client.get(f"/api/history/{transcription_id}", headers=headers).status_code == 200)
        r = client.post(f"/api/history/{transcription_id}/rewrite?profile=email", headers=headers)
        check("smart rewrite", r.status_code == 200, r.text[:120])

    check("history list", client.get("/api/history", headers=headers).status_code == 200)
    check("analytics overview", client.get("/api/analytics/overview", headers=headers).status_code == 200)
    check("router metrics", client.get("/api/ai/router/metrics", headers=headers).status_code == 200)
    check("settings", client.get("/api/settings", headers=headers).status_code == 200)

    if vocab_id:
        check("vocabulary delete", client.delete(f"/api/vocabulary/{vocab_id}", headers=headers).status_code == 204)

    print()
    if failures:
        print(f"{failures} check(s) failed")
        return 1
    print("all checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
