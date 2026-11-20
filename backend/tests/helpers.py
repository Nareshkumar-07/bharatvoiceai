from __future__ import annotations

import io
import math
import struct
import wave


def make_wav(seconds: float = 2.0, freq: float = 220.0, sample_rate: int = 16000,
             amplitude: float = 0.4) -> bytes:
    """Deterministic test tone - real PCM so VAD/peak logic has something to chew."""
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        frames = bytearray()
        for i in range(int(seconds * sample_rate)):
            value = int(amplitude * 32767 * math.sin(2 * math.pi * freq * i / sample_rate))
            frames += struct.pack("<h", value)
        wf.writeframes(bytes(frames))
    return buf.getvalue()


def pcm16(seconds: float = 1.0, freq: float = 220.0, sample_rate: int = 16000) -> bytes:
    frames = bytearray()
    for i in range(int(seconds * sample_rate)):
        frames += struct.pack("<h", int(0.4 * 32767 * math.sin(2 * math.pi * freq * i / sample_rate)))
    return bytes(frames)
