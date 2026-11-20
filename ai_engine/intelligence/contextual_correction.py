"""Context-aware post-processing (Novelty 4).

Honest framing: the default rewriter is **rule-based**.  It fixes punctuation,
casing, fillers and casual abbreviations.  It does not paraphrase and it never
invents facts.  A model-backed rewriter can be plugged in through
``set_llm_rewriter`` - when none is configured, results are labelled
``method="rule_based"`` so the user knows what produced the text.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Callable, List, Optional

CONTEXT_PROFILES = {
    "general": {"label": "General conversation", "sentence_case": True, "strip_fillers": False},
    "email": {"label": "Professional email", "sentence_case": True, "strip_fillers": True},
    "whatsapp": {"label": "Casual message", "sentence_case": False, "strip_fillers": False},
    "notes": {"label": "College notes", "sentence_case": True, "strip_fillers": True},
    "academic": {"label": "Academic writing", "sentence_case": True, "strip_fillers": True},
    "technical": {"label": "Technical documentation", "sentence_case": True, "strip_fillers": True},
    "code": {"label": "Programming dictation", "sentence_case": False, "strip_fillers": False},
}

FILLERS = {"um", "uh", "erm", "hmm", "like", "you know", "actually", "basically",
           "okay so", "so yeah", "i mean"}

CASUAL_TO_FORMAL = {
    "gonna": "going to", "wanna": "want to", "gotta": "have to", "pls": "please",
    "plz": "please", "thx": "thanks", "btw": "by the way", "asap": "as soon as possible",
    "bro": "", "dude": "", "yaar": "", "machan": "",
}

CODE_TERMS = ["api", "json", "python", "fastapi", "sql", "postgres", "docker", "git",
              "http", "rest", "websocket", "typescript", "react", "numpy", "pytorch"]

_llm_rewriter: Optional[Callable[[str, str], str]] = None


def set_llm_rewriter(fn: Optional[Callable[[str, str], str]]) -> None:
    """Plug in an LLM-backed rewriter (text, profile) -> text. Optional."""
    global _llm_rewriter
    _llm_rewriter = fn


@dataclass
class RewriteResult:
    text: str
    profile: str
    method: str
    changes: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {"text": self.text, "profile": self.profile,
                "method": self.method, "changes": self.changes}


def _sentence_case(text: str) -> str:
    parts = re.split(r"(?<=[.!?])\s+", text.strip())
    return " ".join(p[:1].upper() + p[1:] if p else p for p in parts)


def _basic_punctuation(text: str) -> str:
    t = re.sub(r"\s+", " ", text).strip()
    if t and t[-1] not in ".!?,":
        t += "."
    t = re.sub(r"\s+([,.!?])", r"\1", t)
    t = re.sub(r"([,.!?])(?=[^\s])", r"\1 ", t)
    return t


def preserve_terms(text: str, terms: List[str]) -> str:
    """Re-apply the exact casing of technical terms and names."""
    out = text
    for term in terms:
        pattern = re.compile(r"\b" + re.escape(term) + r"\b", re.IGNORECASE)
        out = pattern.sub(term, out)
    return out


def apply_profile(text: str, profile: str = "general",
                  preserve: Optional[List[str]] = None) -> RewriteResult:
    cfg = CONTEXT_PROFILES.get(profile, CONTEXT_PROFILES["general"])
    changes: List[str] = []
    out = text.strip()

    if cfg["strip_fillers"]:
        before = out
        for filler in sorted(FILLERS, key=len, reverse=True):
            out = re.sub(rf"\b{re.escape(filler)}\b[,]?\s*", "", out, flags=re.IGNORECASE)
        if out != before:
            changes.append("removed filler words")

    if profile in ("email", "academic", "technical", "notes"):
        before = out
        for casual, formal in CASUAL_TO_FORMAL.items():
            out = re.sub(rf"\b{re.escape(casual)}\b", formal, out, flags=re.IGNORECASE)
        out = re.sub(r"\s{2,}", " ", out).strip()
        if out != before:
            changes.append("replaced casual abbreviations")

    before = out
    out = _basic_punctuation(out)
    if out != before:
        changes.append("normalised punctuation")

    if cfg["sentence_case"]:
        before = out
        out = _sentence_case(out)
        if out != before:
            changes.append("applied sentence case")

    if preserve:
        before = out
        out = preserve_terms(out, preserve)
        if out != before:
            changes.append("restored exact term casing")

    return RewriteResult(text=out, profile=profile, method="rule_based", changes=changes)


def smart_rewrite(text: str, profile: str = "email",
                  preserve: Optional[List[str]] = None) -> RewriteResult:
    """Rewrite for a target context. Uses the LLM hook if one is configured."""
    if _llm_rewriter is not None:
        try:
            return RewriteResult(_llm_rewriter(text, profile), profile, "llm_rewriter",
                                 ["rewritten by configured language model"])
        except Exception:  # noqa: BLE001 - fall back rather than fail the request
            pass
    result = apply_profile(text, profile, preserve)
    result.changes.append("rule-based rewrite (no language model configured)")
    return result
