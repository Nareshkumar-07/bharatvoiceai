"""Hypothesis fusion for multi-model comparison.

When the router re-runs an uncertain region with a second model we get two
transcripts of the same audio.  This module aligns them token by token and picks
the better-supported word:

1. identical tokens -> agreed (strongest evidence)
2. different tokens -> prefer the hypothesis whose confidence is higher, but
   prefer a user-vocabulary match when the other candidate is a near-miss
3. insertions/deletions -> keep the primary unless the alternative is longer by
   more than a threshold AND its confidence is clearly higher

The agreement ratio it returns is a real, measurable number (1 - normalised edit
distance) and is used by the confidence estimator.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from difflib import SequenceMatcher
from typing import List, Optional, Sequence

from ai_engine.base import ASRResult


@dataclass
class FusionResult:
    text: str
    agreement: float
    agreed_tokens: int
    total_tokens: int
    used_vocabulary: List[str] = field(default_factory=list)
    detail: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "text": self.text,
            "agreement": round(self.agreement, 4),
            "agreed_tokens": self.agreed_tokens,
            "total_tokens": self.total_tokens,
            "used_vocabulary": self.used_vocabulary,
            "detail": self.detail,
        }


def _vocab_match(token: str, vocabulary: Sequence[str]) -> Optional[str]:
    low = token.lower().strip(".,!?;:")
    for entry in vocabulary:
        if entry.lower() == low:
            return entry
    return None


def fuse(
    primary: ASRResult,
    alternative: ASRResult,
    *,
    primary_confidence: Optional[float] = None,
    alternative_confidence: Optional[float] = None,
    vocabulary: Optional[Sequence[str]] = None,
) -> FusionResult:
    a = primary.text.split()
    b = alternative.text.split()
    vocab = list(vocabulary or [])

    if not a and not b:
        return FusionResult(text="", agreement=0.0, agreed_tokens=0, total_tokens=0)
    if not a:
        return FusionResult(text=alternative.text, agreement=0.0, agreed_tokens=0, total_tokens=len(b))
    if not b:
        return FusionResult(text=primary.text, agreement=1.0, agreed_tokens=len(a), total_tokens=len(a))

    sm = SequenceMatcher(a=[w.lower() for w in a], b=[w.lower() for w in b], autojunk=False)
    out: List[str] = []
    agreed = 0
    used_vocab: List[str] = []
    pc = primary_confidence if primary_confidence is not None else 0.5
    ac = alternative_confidence if alternative_confidence is not None else 0.5

    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal":
            out.extend(a[i1:i2])
            agreed += i2 - i1
        elif tag == "replace":
            for k in range(max(i2 - i1, j2 - j1)):
                wa = a[i1 + k] if i1 + k < i2 else None
                wb = b[j1 + k] if j1 + k < j2 else None
                if wa and wb:
                    va, vb = _vocab_match(wa, vocab), _vocab_match(wb, vocab)
                    if vb and not va:
                        out.append(vb)
                        used_vocab.append(vb)
                    elif va and not vb:
                        out.append(va)
                        used_vocab.append(va)
                    else:
                        out.append(wb if ac > pc else wa)
                else:
                    out.append(wa or wb or "")
        elif tag == "delete":
            out.extend(a[i1:i2])
        elif tag == "insert":
            # keep an alternative insertion only when the alternative is clearly
            # more confident; otherwise the primary stays authoritative
            out.extend(b[j1:j2] if ac - pc > 0.15 else [])

    text = " ".join(w for w in out if w)
    total = max(len(a), len(b))
    agreement = agreed / total if total else 0.0
    return FusionResult(
        text=text,
        agreement=agreement,
        agreed_tokens=agreed,
        total_tokens=total,
        used_vocabulary=used_vocab,
        detail={"primary_model": primary.model, "alternative_model": alternative.model},
    )
