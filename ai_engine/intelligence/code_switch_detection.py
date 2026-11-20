"""Fine-grained code-switch detection over recognised tokens.

What this does
--------------
Given recognised text (and optionally word timings from the provider) it assigns a
language to every token, merges tokens into spans, and reports where the speaker
switched.  It distinguishes:

* ``embedded`` - a short run of another language inside the matrix language
  (the classic "Tamil sentence with English nouns" pattern)
* ``matrix``   - the dominant language of the utterance
* ``uncertain``- romanised tokens we cannot attribute confidently

Anti-overclaiming rule: a romanised English-looking token is only counted as an
English switch when it is in the English lexicon.  A romanised Tamil word like
"romba" is never reported as English just because it uses Latin letters.  Tokens
we cannot attribute are marked ``uncertain`` and excluded from the switch count.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

from ai_engine.intelligence.language_detection import (
    LANGUAGE_NAMES,
    token_language,
    tokenize,
)


@dataclass
class Span:
    start_index: int
    end_index: int
    text: str
    language: Optional[str]
    language_name: str
    kind: str  # matrix | embedded | uncertain
    confidence: float
    evidence: str
    start_ms: Optional[int] = None
    end_ms: Optional[int] = None

    def to_dict(self) -> dict:
        return {
            "start_index": self.start_index,
            "end_index": self.end_index,
            "text": self.text,
            "language": self.language,
            "language_name": self.language_name,
            "kind": self.kind,
            "confidence": round(self.confidence, 3),
            "evidence": self.evidence,
            "start_ms": self.start_ms,
            "end_ms": self.end_ms,
        }


@dataclass
class CodeSwitchAnalysis:
    spans: List[Span] = field(default_factory=list)
    tokens: List[dict] = field(default_factory=list)
    primary_language: Optional[str] = None
    languages: List[str] = field(default_factory=list)
    switch_count: int = 0
    code_mixed_ratio: float = 0.0
    is_code_mixed: bool = False
    uncertain_tokens: int = 0
    method: str = "token_script_lexicon"

    def to_dict(self) -> dict:
        return {
            "spans": [s.to_dict() for s in self.spans],
            "tokens": self.tokens,
            "primary_language": self.primary_language,
            "languages": self.languages,
            "switch_count": self.switch_count,
            "code_mixed_ratio": round(self.code_mixed_ratio, 3),
            "is_code_mixed": self.is_code_mixed,
            "uncertain_tokens": self.uncertain_tokens,
            "method": self.method,
        }


def _word_timing(words: Optional[List[dict]], start_index: int, end_index: int) -> tuple[Optional[int], Optional[int]]:
    if not words:
        return None, None
    window = words[start_index : end_index + 1]
    starts = [w.get("start") for w in window if isinstance(w.get("start"), (int, float))]
    ends = [w.get("end") for w in window if isinstance(w.get("end"), (int, float))]
    if not starts or not ends:
        return None, None
    return int(min(starts) * 1000), int(max(ends) * 1000)


def analyze(
    text: str,
    base_language: Optional[str] = None,
    words: Optional[List[dict]] = None,
) -> CodeSwitchAnalysis:
    tokens = tokenize(text)
    if not tokens:
        return CodeSwitchAnalysis()

    tagged = [token_language(t, base_language) for t in tokens]
    # group consecutive tokens with the same language (uncertain tokens follow the
    # previous confident language so a single odd token does not create a span)
    groups: List[dict] = []
    for i, t in enumerate(tagged):
        lang = t.language
        if groups and groups[-1]["language"] == lang:
            groups[-1]["indices"].append(i)
        else:
            groups.append({"language": lang, "indices": [i]})

    counts: dict[str, int] = {}
    for t in tagged:
        if t.language and not t.uncertain:
            counts[t.language] = counts.get(t.language, 0) + 1

    # Matrix-language choice. Token counts alone get this wrong: in
    # "Tomorrow meeting ku presentation ready pannidu" the English nouns
    # outnumber the Tamil function words, yet the sentence is Tamil.  When the
    # caller (or the ASR provider) supplies the utterance language we trust it;
    # otherwise we fall back to confident token counts.
    present = {t.language for t in tagged if t.language}
    if base_language and base_language in present:
        primary = base_language
    else:
        primary = max(counts, key=counts.get) if counts else base_language

    spans: List[Span] = []
    for g in groups:
        idx = g["indices"]
        span_tokens = [tagged[i] for i in idx]
        span_text = " ".join(tokens[i] for i in idx)
        lang = g["language"]
        mean_conf = sum(t.confidence for t in span_tokens) / len(span_tokens)
        uncertain = all(t.uncertain for t in span_tokens)
        if uncertain:
            kind = "uncertain"
        elif lang == primary:
            kind = "matrix"
        else:
            kind = "embedded"
        s_ms, e_ms = _word_timing(words, idx[0], idx[-1])
        spans.append(
            Span(
                start_index=idx[0],
                end_index=idx[-1],
                text=span_text,
                language=lang,
                language_name=LANGUAGE_NAMES.get(lang or "", "Unknown"),
                kind=kind,
                confidence=mean_conf,
                evidence=span_tokens[0].evidence,
                start_ms=s_ms,
                end_ms=e_ms,
            )
        )

    # count transitions between *confident* languages only
    seq = [s.language for s in spans if s.kind in ("matrix", "embedded") and s.language]
    switch_count = sum(1 for a, b in zip(seq, seq[1:]) if a != b)
    embedded_tokens = sum(
        s.end_index - s.start_index + 1 for s in spans if s.kind == "embedded"
    )
    ratio = embedded_tokens / max(1, len(tokens))
    seen = {s.language for s in spans if s.language}
    languages = ([primary] if primary in seen else []) + sorted(seen - {primary})

    return CodeSwitchAnalysis(
        spans=spans,
        tokens=[t.to_dict() for t in tagged],
        primary_language=primary,
        languages=languages,
        switch_count=switch_count,
        code_mixed_ratio=ratio,
        is_code_mixed=len(languages) > 1 and ratio > 0.0,
        uncertain_tokens=sum(1 for t in tagged if t.uncertain),
    )


def segments_from_analysis(analysis: CodeSwitchAnalysis) -> List[dict]:
    """Convert spans into transcription segments for storage/rendering."""
    return [
        {
            "text": s.text,
            "language": s.language,
            "language_name": s.language_name,
            "kind": s.kind,
            "confidence": round(s.confidence, 3) if s.kind != "uncertain" else None,
            "start_ms": s.start_ms or 0,
            "end_ms": s.end_ms or 0,
            "is_uncertain": s.kind == "uncertain",
        }
        for s in analysis.spans
    ]
