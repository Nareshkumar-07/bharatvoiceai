"""Confidence estimation and calibration.

The problem
-----------
Saaras v4 does not return a confidence score.  Whisper returns ``avg_logprob``.
A router cannot compare "no score" with "0.83", and inventing a number would be
dishonest.  So we do two separate, clearly labelled things:

1. **Provider confidence** - used verbatim when the model reports one.
   ``confidence_source = "provider"``.
2. **Proxy confidence** - our own estimate from observable signals (audio level,
   keyterm coverage, script coherence, provider language probability, hypothesis
   agreement).  ``confidence_source = "proxy"`` and
   ``calibrated = False`` until a calibrator has been fitted on evaluation data.

The proxy is a *decision aid for routing*, not a claim about accuracy.  The
default weights and thresholds are engineering defaults, NOT scientifically
validated constants; ``docs/evaluation.md`` explains how to fit and validate them
against your own labelled data.
"""
from __future__ import annotations

import json
import math
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np

from ai_engine.intelligence.language_detection import ENGLISH_LEXICON, tokenize


@dataclass
class ProxyWeights:
    """Engineering defaults. Tune against your evaluation set."""

    audio_quality: float = 0.20
    script_coherence: float = 0.25
    lexicon_coverage: float = 0.20
    language_probability: float = 0.25
    keyterm_coverage: float = 0.10


@dataclass
class ProxySignals:
    provider_confidence: Optional[float] = None
    language_probability: Optional[float] = None
    audio_dbfs: Optional[float] = None
    token_count: int = 0
    attributable_ratio: float = 0.0
    script_coherence: float = 0.0
    keyterm_hits: int = 0
    keyterms_requested: int = 0
    hypothesis_agreement: Optional[float] = None

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class ConfidenceEstimate:
    score: Optional[float]
    source: str            # provider | proxy | none
    calibrated: bool
    components: Dict[str, float] = field(default_factory=dict)
    notes: str = ""

    def to_dict(self) -> dict:
        return {
            "score": None if self.score is None else round(self.score, 4),
            "source": self.source,
            "calibrated": self.calibrated,
            "components": {k: round(v, 4) for k, v in self.components.items()},
            "notes": self.notes,
        }


def _audio_quality_score(dbfs: Optional[float]) -> Optional[float]:
    """Map level in dBFS to 0..1. Below -45 dBFS is essentially silence."""
    if dbfs is None:
        return None
    lo, hi = -45.0, -18.0
    return float(min(1.0, max(0.0, (dbfs - lo) / (hi - lo))))


def compute_signals(
    text: str,
    *,
    provider_confidence: Optional[float] = None,
    language_probability: Optional[float] = None,
    audio_dbfs: Optional[float] = None,
    keyterms: Optional[List[str]] = None,
    hypothesis_agreement: Optional[float] = None,
    attributable_ratio: Optional[float] = None,
    script_coherence: Optional[float] = None,
) -> ProxySignals:
    tokens = tokenize(text)
    lowered = [t.lower() for t in tokens]
    if attributable_ratio is None:
        attributable = sum(1 for t in lowered if t in ENGLISH_LEXICON)
        attributable_ratio = attributable / max(1, len(lowered))
    if script_coherence is None:
        script_coherence = 1.0 if tokens else 0.0
    hits = 0
    if keyterms:
        joined = " ".join(lowered)
        hits = sum(1 for k in keyterms if k and k.lower() in joined)
    return ProxySignals(
        provider_confidence=provider_confidence,
        language_probability=language_probability,
        audio_dbfs=audio_dbfs,
        token_count=len(tokens),
        attributable_ratio=attributable_ratio,
        script_coherence=script_coherence,
        keyterm_hits=hits,
        keyterms_requested=len(keyterms or []),
        hypothesis_agreement=hypothesis_agreement,
    )


class Calibrator:
    """Logistic calibration fitted on (proxy_score, was_correct) pairs.

    ``fit`` uses plain gradient descent so there is no scipy dependency.  Until
    ``is_fitted`` is true, ``apply`` returns the raw proxy score unchanged and
    the caller keeps ``calibrated=False``.
    """

    def __init__(self, weights: Optional[ProxyWeights] = None) -> None:
        self.weights = weights or ProxyWeights()
        self.a = 1.0
        self.b = 0.0
        self.samples = 0
        self._fitted = False

    @property
    def is_fitted(self) -> bool:
        return self._fitted

    def fit(self, scores: List[float], labels: List[int], epochs: int = 400, lr: float = 0.5) -> None:
        if len(scores) != len(labels) or len(scores) < 20:
            raise ValueError("need >= 20 paired (score, label) samples to calibrate")
        x = np.asarray(scores, dtype=np.float64)
        y = np.asarray(labels, dtype=np.float64)
        a, b = 1.0, 0.0
        for _ in range(epochs):
            z = a * x + b
            p = 1.0 / (1.0 + np.exp(-z))
            grad_a = float(np.mean((p - y) * x))
            grad_b = float(np.mean(p - y))
            a -= lr * grad_a
            b -= lr * grad_b
        self.a, self.b, self.samples, self._fitted = float(a), float(b), len(scores), True

    def apply(self, score: float) -> float:
        if not self._fitted:
            return score
        z = self.a * score + self.b
        return float(1.0 / (1.0 + math.exp(-z)))

    def save(self, path: str | Path) -> None:
        Path(path).write_text(
            json.dumps({"a": self.a, "b": self.b, "samples": self.samples, "fitted": self._fitted})
        )

    def load(self, path: str | Path) -> None:
        data = json.loads(Path(path).read_text())
        self.a, self.b = data.get("a", 1.0), data.get("b", 0.0)
        self.samples = data.get("samples", 0)
        self._fitted = bool(data.get("fitted", False))


def estimate(signals: ProxySignals, calibrator: Optional[Calibrator] = None) -> ConfidenceEstimate:
    w = calibrator.weights if calibrator else ProxyWeights()

    if signals.provider_confidence is not None:
        return ConfidenceEstimate(
            score=float(min(1.0, max(0.0, signals.provider_confidence))),
            source="provider",
            calibrated=True,
            components={"provider_confidence": signals.provider_confidence},
            notes="Reported by the model itself.",
        )

    components: Dict[str, float] = {}
    parts: List[tuple[float, float]] = []  # (weight, value)

    aq = _audio_quality_score(signals.audio_dbfs)
    if aq is not None:
        components["audio_quality"] = aq
        parts.append((w.audio_quality, aq))

    if signals.token_count > 0:
        components["lexicon_coverage"] = signals.attributable_ratio
        parts.append((w.lexicon_coverage, signals.attributable_ratio))
        components["script_coherence"] = signals.script_coherence
        parts.append((w.script_coherence, signals.script_coherence))

    if signals.language_probability is not None:
        lp = float(min(1.0, max(0.0, signals.language_probability)))
        components["language_probability"] = lp
        parts.append((w.language_probability, lp))

    if signals.keyterms_requested:
        kc = signals.keyterm_hits / signals.keyterms_requested
        components["keyterm_coverage"] = kc
        parts.append((w.keyterm_coverage, kc))

    if signals.hypothesis_agreement is not None:
        components["hypothesis_agreement"] = signals.hypothesis_agreement

    if not parts:
        return ConfidenceEstimate(score=None, source="none", calibrated=False,
                                  notes="No signal available to estimate confidence.")

    total_w = sum(p[0] for p in parts)
    score = sum(wt * v for wt, v in parts) / total_w if total_w else 0.0

    if signals.hypothesis_agreement is not None:
        # Two models disagreeing is evidence against the transcript, so pull the
        # estimate down rather than averaging it away.
        score = min(score, 0.5 + 0.5 * signals.hypothesis_agreement)

    calibrated = False
    if calibrator and calibrator.is_fitted:
        score = calibrator.apply(score)
        calibrated = True

    return ConfidenceEstimate(
        score=float(min(1.0, max(0.0, score))),
        source="proxy",
        calibrated=calibrated,
        components=components,
        notes=(
            "Proxy estimate from observable signals; not a model probability."
            if not calibrated
            else "Proxy estimate, logistic-calibrated on evaluation data."
        ),
    )
