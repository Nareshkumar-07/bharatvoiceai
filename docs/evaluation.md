# Evaluation

The application refuses to display WER/CER that were not measured. This document
explains how to measure them properly, and what the harness reports.

## Manifest format

One JSON object per line (`eval/manifest.jsonl`):

```json
{"audio":"eval/audio/ta_en_01.wav","reference":"bro inniku college ku late ah varuven because traffic romba jasthi","language":"ta-IN","mode":"transcribe","tags":["code-mixed","ta-en"]}
{"audio":"eval/audio/hi_en_01.wav","reference":"kal meeting hai presentation ready karna hai","language":"hi-IN","mode":"codemix","tags":["code-mixed","hi-en"]}
{"audio":"eval/audio/noisy_01.wav","reference":"submit the report before friday","language":"en-IN","mode":"transcribe","tags":["noisy","road"]}
```

`tags` drive the per-condition breakdown, so the four conditions named in the
brief (quiet room, classroom, road traffic, crowded public) get separate WERs.

## Running

```bash
cd backend
export SARVAM_API_KEY=...          # or enable a local model
python ../scripts/run_evaluation.py --manifest ../eval/manifest.jsonl --out ../eval/reports/run.json
```

The runner calls the same `AdaptiveRouter` the API uses, so the numbers include
routing and fusion effects rather than raw model output.

## What is reported

| Field | Meaning |
|---|---|
| `wer` | corpus word error rate (errors / reference words) |
| `cer` | corpus character error rate |
| `by_tag[tag].wer` | per-condition WER |
| `latency.p50_ms`, `p95_ms`, `mean_ms` | end-to-end engine latency |
| `models_used` | which model actually produced each row |
| `rows[].wer_detail` | S/D/I breakdown per utterance |
| `rows[].escalated`, `alternatives_used` | routing behaviour |
| `rows[].confidence`, `confidence_source` | what the router believed |
| `skipped` | files that could not run, with the reason |

## Language-ID and code-switch accuracy

Not produced automatically: both need **per-token** language labels, which the
manifest does not carry. To measure them, extend each manifest line with:

```json
"token_languages": ["en","en","ta","en","en","ta"]
```

and compare against `ai_engine.intelligence.code_switch_detection.analyze()`
output. Until you do that, `/api/ai/evaluation` reports these metrics as
unavailable rather than estimating them.

## Calibrating the confidence proxy

1. Run a benchmark with `--dump-scores` (see `scripts/run_evaluation.py`).
2. Build `(proxy_score, correct)` pairs: a row is `correct` when its WER is 0.
3. Fit:

```python
from ai_engine.intelligence.confidence_calibration import Calibrator
cal = Calibrator()
cal.fit(scores, labels)          # needs >= 20 pairs
cal.save("models/calibrator.json")
```

4. Load it into the router (`AdaptiveRouter(calibrator=cal)`), and the UI will
   show `calibrated: true` with the sample count.

## Reporting numbers honestly

- State the model and version, the manifest size, and the tag breakdown.
- Report `demo_fixture` rows as excluded; the harness keeps the flag so you can
  filter them out.
- Never quote a WER from a different dataset as this system's performance.
