#!/usr/bin/env python3
"""Run the evaluation harness against a manifest of labelled audio.

    python scripts/run_evaluation.py --manifest eval/manifest.jsonl \
        --out eval/reports/run.json [--limit 20] [--mode transcribe]

Requires a working recognition backend (SARVAM_API_KEY or a local model).
Without one every row is skipped with the reason, and no numbers are invented.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
for p in (str(REPO_ROOT), str(REPO_ROOT / "backend")):
    if p not in sys.path:
        sys.path.insert(0, p)

try:
    from dotenv import load_dotenv

    load_dotenv(REPO_ROOT / ".env")
except Exception:  # noqa: BLE001 - dotenv is optional here
    pass

from ai_engine.evaluation.benchmark import run_manifest, write_report  # noqa: E402
from ai_engine.intelligence.adaptive_router import RouterPolicy  # noqa: E402


async def main() -> int:
    parser = argparse.ArgumentParser(description="BharatVoice evaluation harness")
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--out", default="eval/reports/run.json")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--mode", default=None, choices=["transcribe", "codemix", "translit", "translate", "verbatim"])
    parser.add_argument("--threshold", type=float, default=0.55)
    parser.add_argument("--dump-scores", action="store_true", help="write (proxy_score, correct) pairs for calibration")
    args = parser.parse_args()

    manifest = Path(args.manifest)
    if not manifest.exists():
        print(f"manifest not found: {manifest}", file=sys.stderr)
        return 2

    policy = RouterPolicy(confidence_threshold=args.threshold)
    report = await run_manifest(manifest, policy=policy, mode_override=args.mode, limit=args.limit)

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    write_report(report, out)

    print(f"utterances scored : {len(report.rows)}")
    print(f"skipped           : {len(report.skipped)}")
    print(f"WER               : {report.wer if report.wer is not None else 'not measured'}")
    print(f"CER               : {report.cer if report.cer is not None else 'not measured'}")
    print(f"latency           : {report.latency}")
    print(f"models used       : {report.models_used}")
    if report.skipped:
        print("\nfirst skipped reasons:")
        for item in report.skipped[:5]:
            print(f"  - {item['audio']}: {item['reason']}")
    print(f"\nreport written to {out}")

    demo_rows = [r for r in report.rows if r.get("demo")]
    if demo_rows:
        print(f"\nWARNING: {len(demo_rows)} row(s) came from the demo fixture adapter. "
              "Exclude them before quoting any number.")

    if args.dump_scores:
        pairs = [
            {"score": r["confidence"], "correct": 1 if r["wer_detail"]["errors"] == 0 else 0}
            for r in report.rows
            if r.get("confidence") is not None and not r.get("demo")
        ]
        score_path = out.with_suffix(".scores.json")
        score_path.write_text(json.dumps(pairs, indent=2))
        print(f"{len(pairs)} calibration pairs written to {score_path} "
              "(need >= 20 to fit the calibrator)")

    return 0 if report.rows else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
