"""Audio normalisation helpers shared by the API and the engine."""
from __future__ import annotations

import numpy as np

from ai_engine.base import AudioPayload

TARGET_RATE = 16000


def resample_linear(audio: AudioPayload, target_rate: int = TARGET_RATE) -> AudioPayload:
    """Cheap linear resampling. Fine for ASR front-ends; use sox/librosa if you
    need production-grade anti-aliasing for high sample rates."""
    if audio.sample_rate == target_rate or not audio.data:
        return audio
    src = audio.to_float32()
    n_out = int(len(src) * target_rate / audio.sample_rate)
    if n_out <= 0:
        return AudioPayload(b"", target_rate, 1, 2)
    idx = np.linspace(0, len(src) - 1, n_out)
    out = np.interp(idx, np.arange(len(src)), src)
    pcm = np.clip(out * 32767.0, -32768, 32767).astype(np.int16).tobytes()
    return AudioPayload(pcm, target_rate, 1, 2)


def to_mono(audio: AudioPayload) -> AudioPayload:
    if audio.channels == 1 or not audio.data:
        return audio
    arr = np.frombuffer(audio.data, dtype=np.int16)
    arr = arr.reshape(-1, audio.channels).mean(axis=1)
    return AudioPayload(arr.astype(np.int16).tobytes(), audio.sample_rate, 1, audio.sample_width)


def normalise_peak(audio: AudioPayload, target_dbfs: float = -3.0) -> AudioPayload:
    """Scale so the loudest sample sits near ``target_dbfs``. Skips silence."""
    if not audio.data:
        return audio
    arr = audio.to_float32()
    peak = float(np.abs(arr).max()) if arr.size else 0.0
    if peak <= 1e-6:
        return audio
    target = 10 ** (target_dbfs / 20.0)
    gain = min(target / peak, 8.0)  # never amplify more than +18 dB
    out = np.clip(arr * gain, -1.0, 1.0)
    return AudioPayload(
        (out * 32767.0).astype(np.int16).tobytes(), audio.sample_rate, 1, 2
    )


def prepare_for_asr(audio: AudioPayload, *, normalise: bool = True) -> AudioPayload:
    """The canonical front-end: mono -> 16 kHz -> optional peak normalisation."""
    out = resample_linear(to_mono(audio), TARGET_RATE)
    if normalise:
        out = normalise_peak(out)
    return out
