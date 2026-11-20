# Research novelty — what is claimed, and what is not

This document is deliberately conservative. Each module below is implemented and
unit-tested; each limitation is stated where it exists.

## Novelty 1 — Confidence-guided adaptive ASR routing

**Implemented in** `ai_engine/intelligence/adaptive_router.py`,
`confidence_calibration.py`, `hypothesis_fusion.py`.

Pipeline: segment → language ID → primary ASR → confidence → uncertainty check →
selective alternative ASR → hypothesis fusion → trace.

Guarantees enforced in code:

- at most `max_alternatives` extra calls (default 1);
- escalation only for segments below `confidence_threshold`, and only while the
  latency budget remains;
- fallback on provider failure is explicit (`engine_status="degraded"`);
- every decision is written to `routing_decisions.trace` for later analysis.

**What is not claimed:** the default thresholds (0.55 / 0.40) are engineering
defaults, not validated constants. `Calibrator` fits a logistic map on
`(proxy_score, correct)` pairs, but it stays unfitted — and labelled as such —
until you supply ≥20 labelled samples. A published accuracy improvement would
require the evaluation in `docs/evaluation.md` on your own data.

## Novelty 2 — Fine-grained code-switch detection

**Implemented in** `language_detection.py`, `code_switch_detection.py`.

- Per-token language attribution using Unicode script ranges plus an English
  lexicon and romanised Indic markers.
- Spans classified `matrix` / `embedded` / `uncertain`.
- Shared scripts (Devanagari, Bengali) reported as ambiguous.
- Romanised Tamil is **not** counted as an English switch merely because it uses
  Latin letters; unlisted Latin tokens are marked uncertain and excluded from the
  switch count.

**What is not claimed:** this is a text-level heuristic, not an acoustic LID
model, and its scores are labelled `heuristic`. Acoustic language identification
comes from the ASR provider.

## Novelty 3 — Personalised dialect and vocabulary adaptation

**Implemented in** `vocabulary_adaptation.py`.

Two mechanisms: keyterm prompting (affects the decoder) and guarded
post-correction (affects the text). Corrections require explicit user approval;
nothing is trained on audio; acoustically clear tokens (confidence ≥ 0.85) are
never rewritten.

**What is not claimed:** no acoustic model adaptation, no speaker embedding, no
silent learning. Those are documented as future work.

## Novelty 4 — Context-aware transcription

**Implemented in** `contextual_correction.py`.

Seven profiles change punctuation, casing, filler removal and casual-abbreviation
expansion. `smart_rewrite` uses an optional LLM hook
(`set_llm_rewriter`); without one, output is labelled `method="rule_based"`.

**What is not claimed:** no paraphrasing, no summarisation, no invented content.

## Novelty 5 — Intelligent multiscript output

Native script, romanised and English are separate operations with separate
providers (`/transliterate`, `/translate`, or Saaras modes). Each output records
`method` and `available`, so a failed translation is visibly failed rather than
silently equal to the input.

## Novelty 6 — Noise-resilient recognition

Energy VAD by default, Silero VAD when installed, spectral gate or DeepFilterNet
for suppression. Noise reduction reports `applied: true` only when it actually
ran. Evaluation in noisy conditions requires you to record the set; the harness
supports per-tag WER so a `noisy` tag gets its own number.

## Novelty 7 — Privacy-first processing

Retention is opt-in per recording and in settings; the erasure endpoint removes
all artefacts; the status endpoint states whether a capability is local or
remote (`runtime: "local" | "remote-api"`).

**What is not claimed:** "offline mode" is a preference that prefers local
adapters. It does not turn a remote-only deployment into an offline one, and the
UI says so.

## Reproducing the claims

```bash
cd backend && python -m pytest -q tests/test_engine.py     # module behaviour
python scripts/run_evaluation.py --manifest eval/manifest.jsonl
```

The second command is the only way to produce WER/CER numbers; the API refuses
to guess them.
