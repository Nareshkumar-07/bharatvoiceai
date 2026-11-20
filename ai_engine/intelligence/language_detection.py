"""Linguistic language identification for recognised text.

IMPORTANT SCOPE NOTE
--------------------
This module operates on **text**, after recognition.  It is a script + lexicon
heuristic, not an acoustic LID model.  Acoustic language identification comes
from the ASR provider (Saaras reports ``language_code`` / ``language_probability``)
and is preferred whenever present.  Everything produced here is labelled
``method="script_lexicon_heuristic"`` and ``confidence_source="heuristic"`` so no
consumer can mistake it for a model score.

Devanagari and Bengali script are genuinely shared by more than one language
(Hindi/Marathi, Bengali/Assamese); those cases are reported as ambiguous rather
than silently guessed.
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

# (start, end, language, script) - Unicode blocks for the supported scripts
SCRIPT_RANGES: List[Tuple[int, int, str, str]] = [
    (0x0900, 0x097F, "hi-IN", "Devanagari"),
    (0x0980, 0x09FF, "bn-IN", "Bengali"),
    (0x0A00, 0x0A7F, "pa-IN", "Gurmukhi"),
    (0x0A80, 0x0AFF, "gu-IN", "Gujarati"),
    (0x0B00, 0x0B7F, "or-IN", "Odia"),
    (0x0B80, 0x0BFF, "ta-IN", "Tamil"),
    (0x0C00, 0x0C7F, "te-IN", "Telugu"),
    (0x0C80, 0x0CFF, "kn-IN", "Kannada"),
    (0x0D00, 0x0D7F, "ml-IN", "Malayalam"),
    (0x0600, 0x06FF, "ur-IN", "Arabic"),
]

SCRIPT_SHARING: Dict[str, List[str]] = {
    "Devanagari": ["hi-IN", "mr-IN"],
    "Bengali": ["bn-IN", "as-IN"],
    "Arabic": ["ur-IN"],
}

LANGUAGE_NAMES: Dict[str, str] = {
    "ta-IN": "Tamil", "hi-IN": "Hindi", "te-IN": "Telugu", "ml-IN": "Malayalam",
    "kn-IN": "Kannada", "bn-IN": "Bengali", "mr-IN": "Marathi", "gu-IN": "Gujarati",
    "pa-IN": "Punjabi", "or-IN": "Odia", "as-IN": "Assamese", "ur-IN": "Urdu",
    "en-IN": "English",
}

# High-frequency English words that appear inside Indian code-mixed speech.
# Deliberately a lexicon, not "any Latin word is English".
ENGLISH_LEXICON = {
    "a", "about", "actually", "after", "again", "all", "also", "an", "and", "any",
    "api", "application", "app", "are", "as", "at", "back", "bad", "basically",
    "be", "because", "been", "before", "best", "better", "between", "bit", "both",
    "bro", "bug", "bus", "business", "but", "by", "call", "can", "car", "care",
    "class", "client", "code", "college", "come", "commit", "company", "complete",
    "concept", "confirm", "correct", "could", "data", "database", "day", "deadline",
    "deploy", "design", "did", "do", "document", "does", "don't", "done", "down",
    "email", "even", "ever", "every", "exam", "exactly", "feature", "file", "final",
    "fine", "first", "for", "form", "free", "friday", "friend", "from", "full",
    "get", "give", "go", "going", "good", "got", "great", "group", "had", "half",
    "hand", "happy", "has", "have", "he", "hello", "help", "her", "here", "high",
    "him", "his", "home", "hostel", "how", "i", "idea", "if", "important", "in",
    "internet", "into", "is", "it", "it's", "job", "just", "keep", "know", "last",
    "late", "later", "laptop", "learn", "lecture", "let", "let's", "life", "like",
    "line", "link", "list", "little", "live", "load", "local", "log", "long", "look",
    "lot", "mail", "main", "make", "manager", "many", "market", "may", "maybe", "me",
    "meeting", "message", "minute", "mobile", "moment", "money", "month", "more",
    "morning", "most", "much", "must", "my", "need", "network", "never", "new",
    "next", "nice", "night", "no", "not", "note", "notes", "nothing", "now", "number",
    "of", "off", "office", "ok", "okay", "on", "once", "one", "online", "only",
    "open", "or", "order", "other", "our", "out", "over", "page", "paper", "part",
    "pass", "people", "perfect", "phone", "place", "plan", "please", "point",
    "possible", "presentation", "problem", "process", "product", "project", "proper",
    "pull", "push", "put", "question", "quick", "quite", "ready", "real", "really",
    "reason", "release", "report", "request", "result", "review", "right", "road",
    "room", "run", "same", "say", "schedule", "school", "screenshot", "see", "send",
    "server", "session", "share", "she", "should", "show", "side", "simple", "since",
    "site", "situation", "so", "some", "something", "sorry", "start", "status",
    "stay", "still", "stop", "story", "submit", "sure", "system", "take", "talk",
    "team", "technical", "tell", "test", "tests", "text", "than", "thank", "thanks",
    "that", "the", "their", "them", "then", "there", "these", "they", "thing",
    "think", "this", "those", "though", "through", "time", "timeline", "to", "today",
    "together", "tomorrow", "tonight", "too", "topic", "traffic", "train", "try",
    "two", "under", "understand", "update", "up", "us", "use", "user", "very",
    "version", "wait", "want", "was", "way", "we", "week", "well", "were", "what",
    "when", "where", "which", "while", "who", "why", "will", "with", "without",
    "work", "working", "world", "would", "wrong", "yeah", "year", "yes", "you",
    "your", "zoom",
}

# Romanised Indic function words / markers.  Used only when the text is Latin
# script and the caller says the utterance is Indic (e.g. translit mode).
ROMANIZED_MARKERS: Dict[str, set] = {
    "ta-IN": {"enna", "epdi", "illa", "illai", "irukku", "iruku", "ku", "la", "le",
              "ah", "aa", "romba", "vanakkam", "pannidu", "pannunga", "sollu",
              "inniku", "innaiku", "naalaiku", "varuven", "poi", "seri", "thaan",
              "dhaan", "vendum", "venum", "mudiyala", "sari", "ada", "da", "di",
              "nalla", "nallaa", "konjam", "poga", "vandhu", "sollunga"},
    "hi-IN": {"hai", "nahi", "kya", "kal", "aaj", "kar", "karna", "karo", "mera",
              "tera", "hum", "tum", "yaar", "bhai", "thoda", "bahut", "accha",
              "haan", "kaise", "kyun", "matlab", "abhi", "baad", "tak", "ho", "gaya",
              "raha", "rahi", "diya", "dena", "lena", "chahiye", "bekaar"},
    "te-IN": {"ki", "lo", "ra", "cheyyu", "cheyandi", "pampinchu", "ayyayi", "ayindi",
              "undi", "ledu", "ela", "enti", "nenu", "nuvvu", "meeru", "manam",
              "bagundi", "chala", "konchem", "inka", "kuda"},
    "ml-IN": {"aanu", "alla", "ente", "njan", "ningal", "cheyyu", "cheyyam",
              "poyi", "varam", "nalla", "valare", "kurachu", "pinne", "sheri"},
    "kn-IN": {"ide", "illa", "nanu", "neenu", "nimma", "maadu", "maadi", "beku",
              "channagide", "thumba", "swalpa", "aamele", "haudu"},
    "bn-IN": {"ache", "khub", "kore", "ami", "tumi", "apni", "korbo", "korte",
              "hobe", "na", "ta", "ekhon", "pore"},
}

# Several romanised words are shared across languages ("nalla" is both Tamil and
# Malayalam). Build a reverse index so ambiguity is resolved explicitly instead of
# by dictionary iteration order.
ROMANIZED_INDEX: Dict[str, List[str]] = {}
for _lang, _markers in ROMANIZED_MARKERS.items():
    for _m in _markers:
        ROMANIZED_INDEX.setdefault(_m, []).append(_lang)

_TOKEN_RE = re.compile(r"[\w'’\u0900-\u0DFF\u0600-\u06FF]+", re.UNICODE)


@dataclass
class TokenLanguage:
    token: str
    language: Optional[str]
    script: str
    confidence: float
    evidence: str
    uncertain: bool = False

    def to_dict(self) -> dict:
        return {
            "token": self.token,
            "language": self.language,
            "script": self.script,
            "confidence": round(self.confidence, 3),
            "evidence": self.evidence,
            "uncertain": self.uncertain,
        }


@dataclass
class LanguageVerdict:
    code: Optional[str]
    name: str
    confidence: float
    method: str
    confidence_source: str
    is_reliable: bool
    ambiguous_with: List[str] = field(default_factory=list)
    scores: Dict[str, float] = field(default_factory=dict)
    script_mix: Dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "code": self.code,
            "name": self.name,
            "confidence": round(self.confidence, 3),
            "method": self.method,
            "confidence_source": self.confidence_source,
            "is_reliable": self.is_reliable,
            "ambiguous_with": self.ambiguous_with,
            "scores": {k: round(v, 3) for k, v in self.scores.items()},
            "script_mix": self.script_mix,
        }


def script_of(token: str) -> Tuple[Optional[str], Optional[str]]:
    """Return (language_hint, script_name) for the dominant script of a token."""
    counts: Dict[str, int] = {}
    for ch in token:
        cp = ord(ch)
        for start, end, lang, script in SCRIPT_RANGES:
            if start <= cp <= end:
                counts[script] = counts.get(script, 0) + 1
                break
        else:
            if ch.isalpha():
                counts["Latin"] = counts.get("Latin", 0) + 1
    if not counts:
        return None, None
    script = max(counts, key=counts.get)
    if script == "Latin":
        return None, "Latin"
    for start, end, lang, name in SCRIPT_RANGES:
        if name == script:
            return lang, script
    return None, script


def normalize(token: str) -> str:
    return unicodedata.normalize("NFC", token.strip().strip(".,!?;:\"'()[]{}")).lower()


def token_language(token: str, base_language: Optional[str] = None) -> TokenLanguage:
    lang_hint, script = script_of(token)
    norm = normalize(token)
    if not norm:
        return TokenLanguage(token, base_language, script or "unknown", 0.0, "empty", True)

    if script and script != "Latin":
        shared = SCRIPT_SHARING.get(script, [])
        if len(shared) > 1:
            # Devanagari / Bengali: script tells us the family, not the language.
            chosen = base_language if base_language in shared else lang_hint
            return TokenLanguage(token, chosen, script, 0.7, f"{script} script (shared family)", True)
        return TokenLanguage(token, lang_hint, script, 0.95, f"{script} script")

    # Latin script: three honest possibilities
    if norm in ENGLISH_LEXICON:
        return TokenLanguage(token, "en-IN", "Latin", 0.8, "English lexicon")

    candidates = ROMANIZED_INDEX.get(norm)
    if candidates:
        # A romanised function word IS evidence for an Indic language; it is not
        # an English switch just because it uses Latin letters.
        if base_language and base_language in candidates:
            return TokenLanguage(token, base_language, "Latin", 0.6,
                                 "romanised Indic marker", False)
        if len(candidates) == 1:
            return TokenLanguage(token, candidates[0], "Latin", 0.55,
                                 "romanised Indic marker", False)
        return TokenLanguage(token, base_language or candidates[0], "Latin", 0.4,
                             "romanised marker shared by " + "/".join(candidates), True)
    if base_language and base_language != "en-IN":
        return TokenLanguage(token, base_language, "Latin", 0.35,
                             "assumed romanised base language", True)
    return TokenLanguage(token, "en-IN", "Latin", 0.5, "unlisted Latin token (assumed English)", True)


def tokenize(text: str) -> List[str]:
    return _TOKEN_RE.findall(text or "")


def detect_text_language(text: str, base_language: Optional[str] = None) -> LanguageVerdict:
    tokens = tokenize(text)
    if not tokens:
        return LanguageVerdict(None, "Unknown", 0.0, "script_lexicon_heuristic", "heuristic", False)

    per_token = [token_language(t, base_language) for t in tokens]
    script_mix: Dict[str, int] = {}
    for t in per_token:
        script_mix[t.script] = script_mix.get(t.script, 0) + 1

    scores: Dict[str, float] = {}
    for t in per_token:
        if t.language:
            scores[t.language] = scores.get(t.language, 0.0) + t.confidence

    total = sum(scores.values()) or 1.0
    scores = {k: v / total for k, v in scores.items()}
    code = max(scores, key=scores.get) if scores else None
    confidence = scores.get(code or "", 0.0)

    ambiguous: List[str] = []
    for script, langs in SCRIPT_SHARING.items():
        if script in script_mix and len(langs) > 1:
            ambiguous = [l for l in langs if l != code]

    return LanguageVerdict(
        code=code,
        name=LANGUAGE_NAMES.get(code or "", "Unknown"),
        confidence=confidence,
        method="script_lexicon_heuristic",
        confidence_source="heuristic",
        is_reliable=confidence >= 0.6 and not ambiguous,
        ambiguous_with=ambiguous,
        scores=scores,
        script_mix=script_mix,
    )
