"""Decode uploaded audio into the engine's canonical PCM payload."""
from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path

from ai_engine.base import AudioPayload, AudioPayload as AP


class AudioDecodeError(ValueError):
    pass


def decode_audio(data: bytes, filename: str = "audio.wav") -> AudioPayload:
    suffix = Path(filename).suffix.lower()
    if suffix in (".wav", ".wave") or data[:4] == b"RIFF":
        try:
            return AP.from_wav_bytes(data)
        except Exception as exc:  # noqa: BLE001
            raise AudioDecodeError(f"invalid WAV file: {exc}") from exc

    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise AudioDecodeError(
            f"cannot decode '{suffix or 'unknown'}' without ffmpeg; "
            "send WAV (pcm_s16le, 16 kHz, mono) or install ffmpeg"
        )

    with tempfile.TemporaryDirectory() as tmp:
        src = Path(tmp) / f"input{suffix or '.bin'}"
        dst = Path(tmp) / "out.wav"
        src.write_bytes(data)
        proc = subprocess.run(
            [ffmpeg, "-y", "-loglevel", "error", "-i", str(src),
             "-ac", "1", "-ar", "16000", "-c:a", "pcm_s16le", str(dst)],
            capture_output=True,
        )
        if proc.returncode != 0 or not dst.exists():
            raise AudioDecodeError(
                f"ffmpeg could not decode this file: {proc.stderr.decode()[:200]}"
            )
        return AP.from_wav_bytes(dst.read_bytes())
