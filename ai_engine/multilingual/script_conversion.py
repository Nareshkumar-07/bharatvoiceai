"""Script detection and conversion helpers used by the output tabs."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from ai_engine.intelligence.language_detection import script_of, tokenize

SCRIPT_FOR_LANGUAGE = {
    "ta-IN": "Tamil", "hi-IN": "Devanagari", "mr-IN": "Devanagari", "te-IN": "Telugu",
    "kn-IN": "Kannada", "ml-IN": "Malayalam", "bn-IN": "Bengali", "as-IN": "Bengali",
    "gu-IN": "Gujarati", "pa-IN": "Gurmukhi", "or-IN": "Odia", "ur-IN": "Arabic",
    "en-IN": "Latin",
}


@dataclass
class ScriptProfile:
    dominant_script: Optional[str]
    is_native_script: bool
    is_latin: bool
    is_romanised_indic: bool
    script_counts: dict

    def to_dict(self) -> dict:
        return {
            "dominant_script": self.dominant_script,
            "is_native_script": self.is_native_script,
            "is_latin": self.is_latin,
            "is_romanised_indic": self.is_romanised_indic,
            "script_counts": self.script_counts,
        }


def profile(text: str, expected_language: Optional[str] = None) -> ScriptProfile:
    counts: dict[str, int] = {}
    for token in tokenize(text):
        _, script = script_of(token)
        if script:
            counts[script] = counts.get(script, 0) + 1
    dominant = max(counts, key=counts.get) if counts else None
    is_latin = dominant == "Latin"
    native = SCRIPT_FOR_LANGUAGE.get(expected_language or "")
    return ScriptProfile(
        dominant_script=dominant,
        is_native_script=bool(native and native != "Latin" and dominant == native),
        is_latin=is_latin,
        # Latin text for an Indic language is romanised, not "English"
        is_romanised_indic=bool(is_latin and native and native != "Latin"),
        script_counts=counts,
    )
