"""Evaluation runner.

Input manifest: one JSON object per line

    {"audio": "eval/audio/t1.wav", "reference": "bro inniku college ku late ah varuven",
     "language": "ta-IN", "mode": "transcribe", "tags": ["code-mixed", "ta-en"]}

Output: JSON summary with WER/CER, per-utterance rows, latency percentiles and the
model/routing decision used for each item.  Metrics are only reported for items
that actually ran; anything skipped is listed with the reason.
"""
from __future__ import annotations

import asyncio
import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

from ai_engine.base import AudioPayload
from ai_engine.evaluation.cer import cer
from ai_engine.evaluation.latency import LatencyRecorder
from ai_engine.evaluation.wer import wer
from ai_engine.intelligence.adaptive_router import AdaptiveRouter, RouterPolicy


@dataclass
class BenchmarkReport:
    rows: List[dict] = field(default_factory=list)
    skipped: List[dict] = field(default_factory=list)
    wer: Optional[float] = None
    cer: Optional[float] = None
    latency: dict = field(default_factory=dict)
    models_used: Dict[str, int] = field(default_factory=dict)
    by_tag: Dict[str, dict] = field(default_factory=dict)
    started_at: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "started_at": self.started_at,
            "utterances": len(self.rows),
            "skipped": self.skipped,
            "wer": self.wer,
            "cer": self.cer,
            "latency": self.latency,
            "models_used": self.models_used,
            "by_tag": self.by_tag,
            "rows": self.rows,
        }


def _aggregate(rows: List[dict]) -> tuple[Optional[float], Optional[float]]:
    ref_words = sum(r["wer_detail"]["reference_length"] for r in rows)
    err_words = sum(r["wer_detail"]["errors"] for r in rows)
    ref_chars = sum(r["cer_detail"]["reference_chars"] for r in rows)
    err_chars = sum(r["cer_detail"]["errors"] for r in rows)
    return (
        round(err_words / ref_words, 4) if ref_words else None,
        round(err_chars / ref_chars, 4) if ref_chars else None,
    )


async def run_manifest(manifest_path: str | Path, *, policy: Optional[RouterPolicy] = None,
                       mode_override: Optional[str] = None,
                       limit: Optional[int] = None) -> BenchmarkReport:
    report = BenchmarkReport(started_at=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))
    items = []
    for line in Path(manifest_path).read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            items.append(json.loads(line))
    if limit:
        items = items[:limit]

    router = AdaptiveRouter(policy=policy or RouterPolicy())
    latencies = LatencyRecorder()

    for item in items:
        audio_path = Path(item["audio"])
        if not audio_path.exists():
            report.skipped.append({"audio": str(audio_path), "reason": "file not found"})
            continue
        try:
            audio = AudioPayload.from_wav_bytes(audio_path.read_bytes())
        except Exception as exc:  # noqa: BLE001
            report.skipped.append({"audio": str(audio_path), "reason": f"unreadable wav: {exc}"})
            continue

        t0 = time.perf_counter()
        try:
            outcome = await router.route(
                audio,
                mode=mode_override or item.get("mode", "transcribe"),
                language_code=item.get("language"),
            )
        except Exception as exc:  # noqa: BLE001
            report.skipped.append({"audio": str(audio_path), "reason": f"engine error: {exc}"})
            continue
        elapsed = (time.perf_counter() - t0) * 1000
        latencies.add(elapsed)

        hyp = outcome.result.text
        ref = item.get("reference", "")
        w = wer(ref, hyp)
        c = cer(ref, hyp)
        report.models_used[outcome.primary_model] = report.models_used.get(outcome.primary_model, 0) + 1
        row = {
            "audio": str(audio_path),
            "reference": ref,
            "hypothesis": hyp,
            "language": item.get("language"),
            "mode": outcome.result.mode,
            "model": outcome.primary_model,
            "alternatives_used": outcome.alternatives_used,
            "escalated": outcome.escalated,
            "confidence": outcome.confidence,
            "confidence_source": outcome.confidence_source,
            "engine_status": outcome.result.engine_status,
            "demo": outcome.result.demo,
            "latency_ms": round(elapsed, 1),
            "wer_detail": w.to_dict(),
            "cer_detail": c,
            "tags": item.get("tags", []),
        }
        report.rows.append(row)

        for tag in item.get("tags", []):
            bucket = report.by_tag.setdefault(tag, {"count": 0, "errors": 0, "reference_words": 0})
            bucket["count"] += 1
            bucket["errors"] += w.errors
            bucket["reference_words"] += w.reference_length

    if report.rows:
        report.wer, report.cer = _aggregate(report.rows)
    report.latency = latencies.summary()
    for tag, bucket in report.by_tag.items():
        bucket["wer"] = (round(bucket["errors"] / bucket["reference_words"], 4)
                         if bucket["reference_words"] else None)
    return report


def write_report(report: BenchmarkReport, path: str | Path) -> None:
    Path(path).write_text(json.dumps(report.to_dict(), indent=2, ensure_ascii=False))
