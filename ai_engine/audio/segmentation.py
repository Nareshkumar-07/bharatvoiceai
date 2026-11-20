"""Segment audio for the 30-second REST limit and for router escalation."""
from __future__ import annotations

from typing import List

from ai_engine.audio.vad import energy_vad
from ai_engine.base import AudioPayload

# Saaras REST accepts <=30 s. Leave headroom for resampling/padding.
REST_CHUNK_SECONDS = 28.0


def split_audio(audio: AudioPayload, max_seconds: float = REST_CHUNK_SECONDS) -> List[AudioPayload]:
    """Split into <=max_seconds chunks, preferring a silence boundary."""
    if audio.duration_seconds <= max_seconds:
        return [audio]

    vad = energy_vad(audio)
    boundaries: List[float] = [s.end for s in vad.segments]
    chunks: List[AudioPayload] = []
    start = 0.0
    total = audio.duration_seconds
    while start < total - 0.05:
        limit = min(start + max_seconds, total)
        cut = limit
        if limit < total:
            # nearest silence boundary inside [start + 1s, limit]
            candidates = [b for b in boundaries if start + 1.0 < b <= limit]
            if candidates:
                cut = max(candidates)
        chunks.append(audio.slice_seconds(start, cut))
        start = cut
    return [c for c in chunks if c.data]


def utterance_segments(audio: AudioPayload, *, min_ms: int = 250) -> List[AudioPayload]:
    """VAD-delimited utterances, used by the streaming endpoint."""
    vad = energy_vad(audio)
    out = []
    for seg in vad.segments:
        if (seg.end - seg.start) * 1000 >= min_ms:
            out.append(audio.slice_seconds(seg.start, seg.end))
    return out or [audio]
