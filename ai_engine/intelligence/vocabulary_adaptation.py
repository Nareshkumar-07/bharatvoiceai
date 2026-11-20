"""Personalised vocabulary adaptation (Novelty 3).

Scope, stated plainly
---------------------
This adapts the **text output** using a user-approved dictionary.  It is NOT
acoustic fine-tuning: no model weights change and no private audio is trained on.
The module docstring in ``docs/research_novelty.md`` says the same thing.

Two mechanisms, both real:

1. **Keyterm prompting** - approved vocabulary is passed to Saaras v4 as
   ``keyterms`` so the decoder is biased before it produces text.  This is the
   only mechanism that can change what the model *hears*.
2. **Guarded post-correction** - after recognition, near-miss tokens are mapped
   to the user's preferred spelling.  A replacement is skipped when the token
   carries a confidence at or above ``high_conf_guard`` (acoustically clear
   speech is never rewritten) and when the phonetic distance is too large.
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from difflib import SequenceMatcher
from typing import Iterable, List, Optional, Sequence


@dataclass
class VocabEntry:
    word: str
    preferred_spelling: str
    category: str = "general"
    language_code: str = "en-IN"
    pronunciation_hint: Optional[str] = None
    weight: float = 1.0
    usage_count: int = 0

    @property
    def target(self) -> str:
        return (self.preferred_spelling or self.word).strip()


@dataclass
class AdaptationResult:
    text: str
    applied: List[dict] = field(default_factory=list)
    skipped: List[dict] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {"text": self.text, "applied": self.applied, "skipped": self.skipped}


_VOWELS = "aeiou"


def phonetic_key(word: str) -> str:
    """Language-agnostic rough key.

    Latin words lose vowels and doubled letters (a poor man's Soundex, good
    enough for "naresh"/"nareshh"/"naresh kumar" style near misses).  Indic
    words are normalised but otherwise kept, because script deletion rules differ
    per language and a wrong key is worse than no key.
    """
    w = unicodedata.normalize("NFC", word.strip().lower())
    w = re.sub(r"[^\w\u0900-\u0DFF\u0600-\u06FF]", "", w)
    if not w:
        return ""
    if all(ord(c) < 128 for c in w):
        w = re.sub(r"(.)\1+", r"\1", w)
        return "".join(c for c in w if c not in _VOWELS)
    return w


def similarity(a: str, b: str) -> float:
    return SequenceMatcher(a=a.lower(), b=b.lower()).ratio()


def build_keyterms(entries: Iterable[VocabEntry], limit: int = 50) -> List[str]:
    """Terms for Saaras v4 keyterm prompting (max 50 per the API)."""
    out: List[str] = []
    seen = set()
    for e in sorted(entries, key=lambda x: (-x.weight, -x.usage_count)):
        t = e.target
        if t and t.lower() not in seen:
            seen.add(t.lower())
            out.append(t)
        if len(out) >= limit:
            break
    return out


def apply_vocabulary(
    text: str,
    entries: Sequence[VocabEntry],
    *,
    high_conf_guard: float = 0.85,
    min_similarity: float = 0.72,
    token_confidence: Optional[dict[str, Optional[float]]] = None,
) -> AdaptationResult:
    if not text or not entries:
        return AdaptationResult(text=text)

    by_key: dict[str, VocabEntry] = {}
    for e in entries:
        k = phonetic_key(e.word) or phonetic_key(e.target)
        if k:
            by_key.setdefault(k, e)

    applied: List[dict] = []
    skipped: List[dict] = []
    out_tokens: List[str] = []

    for raw in text.split():
        core = raw.strip(".,!?;:\"'()[]")
        if not core:
            out_tokens.append(raw)
            continue
        entry = by_key.get(phonetic_key(core))
        if entry is None:
            # try similarity against preferred spellings for multi-word names
            best, best_sim = None, 0.0
            for e in entries:
                sim = similarity(core, e.word)
                if sim > best_sim:
                    best, best_sim = e, sim
            if best is not None and best_sim >= 0.9:
                entry = best
            else:
                out_tokens.append(raw)
                continue

        if core == entry.target:
            # exact match already - nothing to change
            out_tokens.append(raw)
            continue

        conf = (token_confidence or {}).get(core)
        if conf is not None and conf >= high_conf_guard:
            skipped.append({"token": core, "candidate": entry.target,
                            "reason": f"acoustic confidence {conf:.2f} >= guard {high_conf_guard}"})
            out_tokens.append(raw)
            continue
        if similarity(core, entry.word) < min_similarity:
            skipped.append({"token": core, "candidate": entry.target,
                            "reason": "phonetic distance too large"})
            out_tokens.append(raw)
            continue

        replacement = raw.replace(core, entry.target)
        out_tokens.append(replacement)
        applied.append({"token": core, "replaced_with": entry.target,
                        "category": entry.category, "language": entry.language_code})

    return AdaptationResult(text=" ".join(out_tokens), applied=applied, skipped=skipped)
