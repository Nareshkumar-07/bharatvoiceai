"""Engine unit tests: language ID, code-switching, fusion, vocabulary, routing."""
from __future__ import annotations

import pytest

from ai_engine.base import ASRAdapter, ASRResult, AdapterUnavailable, AudioPayload, SegmentResult, WordToken
from ai_engine.evaluation.cer import cer
from ai_engine.evaluation.wer import wer
from ai_engine.intelligence.adaptive_router import AdaptiveRouter, RouterPolicy
from ai_engine.intelligence.code_switch_detection import analyze as cs_analyze
from ai_engine.intelligence.confidence_calibration import Calibrator, ProxySignals, estimate
from ai_engine.intelligence.contextual_correction import apply_profile
from ai_engine.intelligence.hypothesis_fusion import fuse
from ai_engine.intelligence.language_detection import detect_text_language, token_language
from ai_engine.intelligence.vocabulary_adaptation import (
    VocabEntry,
    apply_vocabulary,
    build_keyterms,
    phonetic_key,
)
from tests.helpers import pcm16


# --------------------------------------------------------------------------- #
# Language identification
# --------------------------------------------------------------------------- #
def test_script_detection_tamil():
    verdict = detect_text_language("நாளைக்கு காலேஜுக்கு லேட்டா வருவேன்")
    assert verdict.code == "ta-IN"
    assert verdict.confidence_source == "heuristic"


def test_devanagari_is_reported_ambiguous():
    verdict = detect_text_language("कल मीटिंग है")
    assert verdict.code in ("hi-IN", "mr-IN")
    assert "mr-IN" in verdict.ambiguous_with or "hi-IN" in verdict.ambiguous_with


def test_romanised_indic_not_labelled_english():
    tok = token_language("romba", base_language="ta-IN")
    assert tok.language == "ta-IN", "romanised Tamil must not be tagged as English"
    assert tok.uncertain is False


def test_shared_romanised_marker_is_uncertain():
    tok = token_language("nalla", base_language=None)
    assert tok.uncertain is True, "a word shared by Tamil and Malayalam is ambiguous"


def test_english_word_in_tamil_sentence():
    tok = token_language("meeting", base_language="ta-IN")
    assert tok.language == "en-IN"


# --------------------------------------------------------------------------- #
# Code switching
# --------------------------------------------------------------------------- #
def test_code_switch_spans_are_labelled():
    analysis = cs_analyze("Tomorrow meeting ku presentation ready pannidu", "ta-IN")
    assert analysis.is_code_mixed
    assert analysis.switch_count >= 1
    languages = set(analysis.languages)
    assert "ta-IN" in languages
    assert any(s.kind == "embedded" for s in analysis.spans)


def test_pure_tamil_has_no_switches():
    analysis = cs_analyze("நாளைக்கு காலேஜுக்கு லேட்டா வருவேன்", "ta-IN")
    assert analysis.switch_count == 0
    assert analysis.is_code_mixed is False


def test_uncertain_tokens_do_not_create_false_switches():
    analysis = cs_analyze("romba nalla irukku", "ta-IN")
    assert analysis.switch_count == 0


# --------------------------------------------------------------------------- #
# Metrics
# --------------------------------------------------------------------------- #
def test_wer_identical():
    stats = wer("hello world", "hello world")
    assert stats.errors == 0
    assert stats.rate == 0.0


def test_wer_substitution_and_cer():
    stats = wer("bro inniku college late", "bro today college late")
    assert stats.substitutions >= 1
    c = cer("abc", "abd")
    assert c["cer"] == pytest.approx(1 / 3, abs=1e-3)


# --------------------------------------------------------------------------- #
# Confidence + calibration
# --------------------------------------------------------------------------- #
def test_provider_confidence_passes_through():
    est = estimate(ProxySignals(provider_confidence=0.82))
    assert est.source == "provider"
    assert est.score == pytest.approx(0.82)
    assert est.calibrated is True


def test_proxy_confidence_is_labelled_uncalibrated():
    est = estimate(ProxySignals(token_count=5, attributable_ratio=0.6, script_coherence=0.8,
                                audio_dbfs=-20.0))
    assert est.source == "proxy"
    assert est.calibrated is False
    assert 0.0 <= est.score <= 1.0


def test_calibrator_fit_requires_samples():
    with pytest.raises(ValueError):
        Calibrator().fit([0.9], [1])


def test_calibrator_fit_shifts_scores():
    scores = [0.1, 0.2, 0.3, 0.4, 0.8, 0.9] * 5
    labels = [0, 0, 0, 0, 1, 1] * 5
    cal = Calibrator()
    cal.fit(scores, labels)
    assert cal.is_fitted
    assert cal.apply(0.9) > cal.apply(0.1)


# --------------------------------------------------------------------------- #
# Fusion + vocabulary
# --------------------------------------------------------------------------- #
def _result(text: str, model: str = "m1", conf=None) -> ASRResult:
    return ASRResult(text=text, provider="test", model=model, confidence=conf,
                     segments=[SegmentResult(text=text, words=[WordToken(text=w) for w in text.split()])])


def test_fusion_prefers_agreement():
    primary = _result("bro inniku college late", "a")
    alt = _result("bro inniku college late", "b")
    out = fuse(primary, alt)
    assert out.agreement == 1.0
    assert out.text == primary.text


def test_fusion_uses_vocabulary_spelling():
    primary = _result("naresh is here")
    alt = _result("nareshh is here")
    out = fuse(primary, alt, vocabulary=["Naresh"])
    assert "Naresh" in out.text


def test_vocabulary_applies_preferred_spelling():
    entries = [VocabEntry(word="naresh", preferred_spelling="Naresh", category="personal_name")]
    out = apply_vocabulary("hi naresh how are you", entries)
    assert "Naresh" in out.text
    assert out.applied


def test_vocabulary_respects_high_confidence_guard():
    entries = [VocabEntry(word="naresh", preferred_spelling="Naresh")]
    out = apply_vocabulary("hi naresh", entries, token_confidence={"naresh": 0.95})
    assert "Naresh" not in out.text
    assert out.skipped


def test_keyterms_limited_to_fifty():
    entries = [VocabEntry(word=f"word{i}", preferred_spelling=f"Word{i}") for i in range(80)]
    assert len(build_keyterms(entries)) == 50


def test_phonetic_key_collapses_variants():
    assert phonetic_key("Naresh") == phonetic_key("nareshh")


# --------------------------------------------------------------------------- #
# Context correction
# --------------------------------------------------------------------------- #
def test_email_profile_cleans_casual_text():
    out = apply_profile("bro gonna send the report pls check", "email")
    assert "bro" not in out.text.lower()
    assert "going to" in out.text.lower()
    assert out.method == "rule_based"


def test_code_profile_preserves_case():
    out = apply_profile("run npm build", "code")
    assert "npm" in out.text


# --------------------------------------------------------------------------- #
# Router
# --------------------------------------------------------------------------- #
class FakeAdapter(ASRAdapter):
    def __init__(self, model_id: str, text: str, confidence=None, available=True,
                 fail=False, mode="transcribe"):
        self.model_id = model_id
        self.provider = "fake"
        self.supports_modes = (mode,)
        self.returns_confidence = confidence is not None
        self.text = text
        self.confidence = confidence
        self.available = available
        self.fail = fail
        self.calls = 0

    async def is_available(self):
        return (self.available, None if self.available else "disabled for test")

    async def transcribe(self, audio, *, mode="transcribe", language_code=None,
                         keyterms=None, context=None):
        self.calls += 1
        if self.fail:
            raise AdapterUnavailable(self.model_id, "forced failure")
        return ASRResult(
            text=self.text, provider="fake", model=self.model_id, mode=mode,
            language=language_code, confidence=self.confidence,
            confidence_source="provider" if self.confidence is not None else None,
            segments=[SegmentResult(text=self.text, start=0.0, end=audio.duration_seconds,
                                    words=[WordToken(text=w) for w in self.text.split()])],
            latency_ms=1.0,
        )


@pytest.mark.asyncio
async def test_router_accepts_confident_primary():
    primary = FakeAdapter("saaras:v4", "bro inniku college late", confidence=0.92)
    alt = FakeAdapter("whisper", "something else entirely")
    router = AdaptiveRouter(adapters={"saaras:v4": primary, "whisper": alt},
                            policy=RouterPolicy())
    audio = AudioPayload(pcm16(1.0))
    outcome = await router.route(audio, mode="transcribe")
    assert outcome.primary_model == "saaras:v4"
    assert outcome.escalated is False
    assert alt.calls == 0, "must not run the alternative for a confident result"


@pytest.mark.asyncio
async def test_router_escalates_low_confidence():
    primary = FakeAdapter("saaras:v4", "bro inniku college", confidence=0.21)
    alt = FakeAdapter("whisper", "bro inniku college", confidence=0.9)
    router = AdaptiveRouter(adapters={"saaras:v4": primary, "whisper": alt},
                            policy=RouterPolicy(confidence_threshold=0.55))
    outcome = await router.route(audio=AudioPayload(pcm16(1.0)), mode="transcribe")
    assert outcome.escalated is True
    assert "whisper" in outcome.alternatives_used
    assert alt.calls >= 1
    assert any(t["step"] == "fuse" for t in outcome.trace)


@pytest.mark.asyncio
async def test_router_falls_back_when_primary_fails():
    primary = FakeAdapter("saaras:v4", "", fail=True)
    alt = FakeAdapter("whisper", "fallback text here", confidence=0.8)
    router = AdaptiveRouter(adapters={"saaras:v4": primary, "whisper": alt})
    outcome = await router.route(audio=AudioPayload(pcm16(1.0)), mode="transcribe")
    assert outcome.result.text == "fallback text here"
    assert outcome.result.engine_status == "degraded"


@pytest.mark.asyncio
async def test_router_rejects_silence():
    primary = FakeAdapter("saaras:v4", "text", confidence=0.9)
    router = AdaptiveRouter(adapters={"saaras:v4": primary})
    silent = AudioPayload(b"\x00\x00" * 16000)
    with pytest.raises(Exception):
        await router.route(audio=silent, mode="transcribe")


@pytest.mark.asyncio
async def test_router_raises_when_nothing_available():
    primary = FakeAdapter("saaras:v4", "x", available=False)
    router = AdaptiveRouter(adapters={"saaras:v4": primary})
    with pytest.raises(AdapterUnavailable):
        await router.route(audio=AudioPayload(pcm16(1.0)), mode="transcribe")
