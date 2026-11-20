"""Optional noise suppression.

DeepFilterNet gives real, measurable noise suppression but pulls in torch and
model weights.  When it is not installed we say so instead of quietly returning
the input and calling it "enhanced".
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import numpy as np

from ai_engine.base import AudioPayload
from app.config import settings
from app.core.logging import get_logger

log = get_logger("ai_engine.noise")


@dataclass
class DenoiseResult:
    audio: AudioPayload
    applied: bool
    method: str
    reason: Optional[str] = None
    noise_floor_dbfs: Optional[float] = None

    def to_dict(self) -> dict:
        return {
            "applied": self.applied,
            "method": self.method,
            "reason": self.reason,
            "noise_floor_dbfs": self.noise_floor_dbfs,
        }


def estimate_noise_floor(audio: AudioPayload) -> Optional[float]:
    if not audio.data:
        return None
    x = audio.to_float32()
    frame = int(audio.sample_rate * 0.03)
    n = len(x) // frame
    if n < 5:
        return None
    rms = np.sqrt(np.mean(x[: n * frame].reshape(n, frame) ** 2, axis=1) + 1e-12)
    db = 20 * np.log10(rms + 1e-12)
    return float(np.percentile(db, 10))  # 10th percentile ~ noise floor


def spectral_gate(audio: AudioPayload, reduction_db: float = 12.0) -> AudioPayload:
    """Lightweight spectral subtraction - the honest fallback when DeepFilterNet
    is not installed. It is not a neural denoiser and is labelled as such."""
    x = audio.to_float32()
    if len(x) < 1024:
        return audio
    frame, hop = 512, 256
    window = np.hanning(frame).astype(np.float32)
    noise_mag = np.abs(np.fft.rfft(x[:frame] * window))
    out = np.zeros_like(x)
    gain_floor = 10 ** (-reduction_db / 20.0)
    for i in range(0, len(x) - frame, hop):
        spec = np.fft.rfft(x[i : i + frame] * window)
        mag, phase = np.abs(spec), np.angle(spec)
        gain = np.maximum(mag - noise_mag, gain_floor * mag) / (mag + 1e-9)
        out[i : i + frame] += np.fft.irfft(mag * gain * np.exp(1j * phase)).astype(np.float32) * window
    out = np.clip(out, -1.0, 1.0)
    return AudioPayload((out * 32767).astype(np.int16).tobytes(), audio.sample_rate, 1, 2)


def reduce_noise(audio: AudioPayload, enabled: bool = True) -> DenoiseResult:
    floor = estimate_noise_floor(audio)
    if not enabled:
        return DenoiseResult(audio, False, "none", "noise reduction disabled", floor)

    if settings.deepfilternet_enabled:
        try:
            from df.enhance import enhance, init_df  # type: ignore
            import torch

            model, state, _ = init_df()
            tensor = torch.from_numpy(audio.to_float32()).unsqueeze(0)
            enhanced = enhance(model, state, tensor).squeeze(0).numpy()
            pcm = (np.clip(enhanced, -1, 1) * 32767).astype(np.int16).tobytes()
            return DenoiseResult(
                AudioPayload(pcm, audio.sample_rate, 1, 2), True, "deepfilternet", None, floor
            )
        except Exception as exc:  # noqa: BLE001
            log.warning("DeepFilterNet failed (%s); falling back to spectral gate", exc)

    return DenoiseResult(spectral_gate(audio), True, "spectral_gate",
                         "DeepFilterNet unavailable - used spectral subtraction", floor)
