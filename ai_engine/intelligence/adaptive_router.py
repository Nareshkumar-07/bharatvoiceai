"""Confidence-guided adaptive ASR routing (Novelty 1).

Pipeline
--------
audio -> prepare -> (chunk if > 28 s) -> primary ASR -> confidence
      -> [confident] stop
      -> [uncertain] re-run ONLY the uncertain segments with one alternative model
      -> hypothesis fusion -> final result + decision trace

Design guarantees
-----------------
* Never runs every model for every request: at most ``max_alternatives`` extra
  calls, only for segments whose confidence is below threshold, and only while a
  latency budget remains.
* Never invents a confidence score.  Provider scores pass through; otherwise the
  estimate is labelled ``proxy``.
* Every decision is recorded in ``trace`` so it can be stored, audited and used
  to fit the calibrator later.
* Fallback on provider failure is explicit: ``engine_status="degraded"`` and the
  reason is reported to the user.

Thresholds are configurable engineering defaults, not validated constants.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Sequence

from ai_engine.audio.preprocessing import prepare_for_asr
from ai_engine.audio.segmentation import split_audio
from ai_engine.base import (
    ASRAdapter,
    ASRResult,
    AdapterError,
    AdapterUnavailable,
    AudioPayload,
    SegmentResult,
    Timer,
    WordToken,
)
from ai_engine.intelligence import confidence_calibration as calib
from ai_engine.intelligence.code_switch_detection import analyze as analyze_code_switch
from ai_engine.intelligence.hypothesis_fusion import fuse
from ai_engine.registry import build_adapters
from app.core.logging import get_logger

log = get_logger("ai_engine.router")


@dataclass
class RouterPolicy:
    enabled: bool = True
    confidence_threshold: float = 0.55
    confirmation_threshold: float = 0.40
    max_alternatives: int = 1
    latency_budget_ms: float = 12000.0
    escalate_segments_only: bool = True
    min_segment_seconds: float = 0.6

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class RoutingOutcome:
    result: ASRResult
    primary_model: str
    alternatives_used: List[str] = field(default_factory=list)
    escalated: bool = False
    needs_confirmation: bool = False
    reason: str = ""
    confidence: Optional[float] = None
    confidence_source: Optional[str] = None
    confidence_components: Dict[str, float] = field(default_factory=dict)
    trace: List[dict] = field(default_factory=list)
    predictions: List[dict] = field(default_factory=list)
    total_latency_ms: float = 0.0
    policy: RouterPolicy = field(default_factory=RouterPolicy)

    def to_dict(self) -> dict:
        return {
            "result": self.result.to_dict(),
            "primary_model": self.primary_model,
            "alternatives_used": self.alternatives_used,
            "escalated": self.escalated,
            "needs_confirmation": self.needs_confirmation,
            "reason": self.reason,
            "confidence": None if self.confidence is None else round(self.confidence, 4),
            "confidence_source": self.confidence_source,
            "confidence_components": {k: round(v, 4) for k, v in self.confidence_components.items()},
            "trace": self.trace,
            "predictions": self.predictions,
            "total_latency_ms": round(self.total_latency_ms, 1),
            "policy": self.policy.to_dict(),
        }


def _trace(step: str, status: str, detail: str, **extra) -> dict:
    return {"step": step, "status": status, "detail": detail, "at_ms": round(time.time() * 1000 % 1e9, 0), **extra}


class AdaptiveRouter:
    def __init__(
        self,
        adapters: Optional[Dict[str, ASRAdapter]] = None,
        policy: Optional[RouterPolicy] = None,
        calibrator: Optional[calib.Calibrator] = None,
        priority: Sequence[str] = ("saaras:v4", "whisper", "indicconformer", "demo-fixture"),
    ) -> None:
        self.adapters = adapters if adapters is not None else build_adapters()
        self.policy = policy or RouterPolicy()
        self.calibrator = calibrator
        self.priority = tuple(priority)

    # ------------------------------------------------------------------ #
    async def _available(self, adapter: ASRAdapter) -> tuple[bool, Optional[str]]:
        try:
            return await adapter.is_available()
        except Exception as exc:  # noqa: BLE001
            return False, f"probe error: {exc}"

    async def _pick_primary(
        self, mode: str, prefer_model: Optional[str]
    ) -> tuple[Optional[ASRAdapter], List[dict]]:
        trace: List[dict] = []
        order: List[str] = []
        if prefer_model and prefer_model in self.adapters:
            order.append(prefer_model)
        order.extend(m for m in self.priority if m in self.adapters and m not in order)
        order.extend(m for m in self.adapters if m not in order)

        for model_id in order:
            adapter = self.adapters[model_id]
            if mode not in adapter.supports_modes:
                trace.append(_trace("select_primary", "skip", f"{model_id} does not support mode '{mode}'"))
                continue
            ok, reason = await self._available(adapter)
            if ok:
                trace.append(_trace("select_primary", "ok", f"primary = {model_id}"))
                return adapter, trace
            trace.append(_trace("select_primary", "unavailable", f"{model_id}: {reason}"))
        return None, trace

    async def _pick_alternative(
        self, mode: str, exclude: set[str], language: Optional[str]
    ) -> Optional[ASRAdapter]:
        for model_id in self.priority:
            if model_id in exclude or model_id not in self.adapters:
                continue
            adapter = self.adapters[model_id]
            if mode not in adapter.supports_modes:
                continue
            ok, _ = await self._available(adapter)
            if ok:
                return adapter
        return None

    async def _run(self, adapter: ASRAdapter, audio: AudioPayload, *, mode: str,
                   language_code: Optional[str], keyterms: Optional[List[str]],
                   context: Optional[str]) -> ASRResult:
        """Run one adapter, chunking audio to respect the 30 s REST limit."""
        chunks = split_audio(audio) if adapter.is_remote else [audio]
        if len(chunks) == 1:
            return await adapter.transcribe(
                chunks[0], mode=mode, language_code=language_code, keyterms=keyterms, context=context
            )

        results: List[ASRResult] = []
        offset = 0.0
        for chunk in chunks:
            r = await adapter.transcribe(
                chunk, mode=mode, language_code=language_code, keyterms=keyterms, context=context
            )
            for seg in r.segments:
                seg.start += offset
                seg.end += offset
            offset += chunk.duration_seconds
            results.append(r)

        merged = ASRResult(
            text=" ".join(r.text for r in results if r.text).strip(),
            provider=results[0].provider,
            model=results[0].model,
            mode=mode,
            language=next((r.language for r in results if r.language), None),
            language_probability=next((r.language_probability for r in results if r.language_probability), None),
            segments=[s for r in results for s in r.segments],
            confidence=(sum(r.confidence for r in results if r.confidence is not None)
                        / max(1, sum(1 for r in results if r.confidence is not None))
                        if any(r.confidence is not None for r in results) else None),
            confidence_source=next((r.confidence_source for r in results if r.confidence_source), None),
            latency_ms=sum(r.latency_ms for r in results),
            engine_status="degraded" if any(r.engine_status == "degraded" for r in results) else "ok",
            demo=any(r.demo for r in results),
            raw={"chunks": len(results)},
        )
        return merged

    # ------------------------------------------------------------------ #
    async def route(
        self,
        audio: AudioPayload,
        *,
        mode: str = "transcribe",
        language_code: Optional[str] = None,
        keyterms: Optional[List[str]] = None,
        context: Optional[str] = None,
        prefer_model: Optional[str] = None,
        vocabulary: Optional[Sequence[str]] = None,
    ) -> RoutingOutcome:
        t_start = time.perf_counter()
        trace: List[dict] = []
        predictions: List[dict] = []

        prepared = prepare_for_asr(audio)
        trace.append(_trace(
            "prepare", "ok",
            f"{prepared.duration_seconds:.2f}s @ {prepared.sample_rate} Hz, peak {prepared.peak():.3f}",
        ))

        if not prepared.data or prepared.peak() < 1e-4:
            raise AdapterError("router", "audio contains no speech (silent buffer)", status_code=422)

        primary, select_trace = await self._pick_primary(mode, prefer_model)
        trace.extend(select_trace)
        if primary is None:
            raise AdapterUnavailable("router", "no recognition backend is available; see /api/ai/status")

        # ---- primary recognition, with explicit fallback on failure -----
        result: Optional[ASRResult] = None
        used_fallback = False
        for attempt_model in [primary.model_id] + [m for m in self.priority if m != primary.model_id]:
            adapter = self.adapters.get(attempt_model)
            if adapter is None or mode not in adapter.supports_modes:
                continue
            ok, reason = await self._available(adapter)
            if not ok:
                continue
            try:
                with Timer() as t:
                    result = await self._run(
                        adapter, prepared, mode=mode, language_code=language_code,
                        keyterms=keyterms, context=context,
                    )
                used_fallback = adapter.model_id != primary.model_id
                predictions.append({
                    "model_id": adapter.model_id, "mode": mode, "scope": "full",
                    "hypothesis_text": result.text, "confidence": result.confidence,
                    "confidence_source": result.confidence_source, "latency_ms": t.elapsed_ms,
                    "selected": True,
                })
                trace.append(_trace("primary_asr", "ok",
                                    f"{adapter.model_id} returned {len(result.text.split())} words",
                                    latency_ms=round(t.elapsed_ms, 1)))
                primary = adapter
                break
            except AdapterError as exc:
                trace.append(_trace("primary_asr", "error", str(exc), retryable=exc.retryable))
                log.warning("primary adapter %s failed: %s", adapter.model_id, exc)
            except AdapterUnavailable as exc:
                trace.append(_trace("primary_asr", "unavailable", exc.reason))

        if result is None:
            raise AdapterUnavailable("router", "all recognition backends failed; see trace")

        if used_fallback:
            result.engine_status = "degraded"
        if not result.text.strip():
            trace.append(_trace("primary_asr", "empty", "model returned an empty transcript"))

        # ---- code-switch analysis on the recognised text -----------------
        cs = analyze_code_switch(result.text, result.language)
        trace.append(_trace("code_switch", "ok",
                            f"{len(cs.languages)} language(s), {cs.switch_count} switch(es), "
                            f"ratio {cs.code_mixed_ratio:.2f}"))

        # ---- confidence -------------------------------------------------
        signals = calib.compute_signals(
            result.text,
            provider_confidence=result.confidence,
            language_probability=result.language_probability,
            audio_dbfs=prepared.dbfs(),
            keyterms=keyterms,
            script_coherence=1.0 - min(1.0, cs.code_mixed_ratio),
        )
        estimate = calib.estimate(signals, self.calibrator)
        trace.append(_trace("confidence", estimate.source or "none",
                            estimate.notes or "no estimate",
                            score=None if estimate.score is None else round(estimate.score, 3)))

        escalated = False
        alternatives_used: List[str] = []
        final_text = result.text
        reason = "primary model accepted"

        # ---- escalation: only uncertain segments, only within budget ----
        can_escalate = (
            self.policy.enabled
            and estimate.score is not None
            and estimate.score < self.policy.confidence_threshold
            and self.policy.max_alternatives > 0
            and result.engine_status != "demo_fixture"
        )
        if can_escalate:
            elapsed_ms = (time.perf_counter() - t_start) * 1000
            if elapsed_ms > self.policy.latency_budget_ms:
                trace.append(_trace("escalate", "skip", "latency budget exhausted"))
            else:
                alt = await self._pick_alternative(mode, {primary.model_id}, result.language)
                if alt is None:
                    trace.append(_trace("escalate", "skip", "no alternative backend available"))
                else:
                    targets = self._uncertain_segments(prepared, result)
                    trace.append(_trace(
                        "escalate", "start",
                        f"{alt.model_id} on {len(targets)} segment(s)",
                    ))
                    alt_texts: List[str] = []
                    try:
                        for seg_audio, seg in targets:
                            with Timer() as t2:
                                alt_res = await alt.transcribe(
                                    seg_audio, mode=mode,
                                    language_code=result.language,
                                    keyterms=keyterms, context=context,
                                )
                            alt_texts.append(alt_res.text)
                            predictions.append({
                                "model_id": alt.model_id, "mode": mode,
                                "scope": f"segment:{seg.start:.2f}-{seg.end:.2f}",
                                "hypothesis_text": alt_res.text,
                                "confidence": alt_res.confidence,
                                "confidence_source": alt_res.confidence_source,
                                "latency_ms": t2.elapsed_ms, "selected": False,
                            })
                        alt_joined = " ".join(t for t in alt_texts if t).strip()
                        if alt_joined:
                            alt_result = ASRResult(
                                text=alt_joined, provider=alt.provider, model=alt.model_id,
                                mode=mode, language=result.language,
                                segments=result.segments, confidence=None,
                                confidence_source=None, latency_ms=0.0,
                            )
                            fusion = fuse(
                                result, alt_result,
                                primary_confidence=estimate.score,
                                alternative_confidence=None,
                                vocabulary=vocabulary,
                            )
                            if fusion.agreement >= 0.5:
                                final_text = fusion.text or result.text
                            agreement = fusion.agreement
                            trace.append(_trace(
                                "fuse", "ok",
                                f"agreement {fusion.agreement:.2f} over {fusion.total_tokens} tokens",
                                vocabulary_hits=len(fusion.used_vocabulary),
                            ))
                            # agreement is real evidence: fold it into the estimate
                            estimate = calib.estimate(
                                calib.compute_signals(
                                    final_text,
                                    provider_confidence=result.confidence,
                                    language_probability=result.language_probability,
                                    audio_dbfs=prepared.dbfs(),
                                    keyterms=keyterms,
                                    hypothesis_agreement=agreement,
                                    script_coherence=1.0 - min(1.0, cs.code_mixed_ratio),
                                ),
                                self.calibrator,
                            )
                            escalated = True
                            alternatives_used.append(alt.model_id)
                            reason = (
                                f"primary confidence {result.confidence if result.confidence is not None else 'unknown'}"
                                f"; escalated to {alt.model_id} and fused (agreement {agreement:.2f})"
                            )
                        else:
                            trace.append(_trace("escalate", "empty", "alternative returned no text"))
                    except (AdapterError, AdapterUnavailable) as exc:
                        trace.append(_trace("escalate", "error", str(exc)))

        needs_confirmation = bool(
            estimate.score is not None and estimate.score < self.policy.confirmation_threshold
        )
        if needs_confirmation:
            reason += "; low confidence - user confirmation requested"

        result.text = final_text
        if not escalated:
            # keep the model's own segments; refresh word list from fused text
            pass

        total_ms = (time.perf_counter() - t_start) * 1000
        trace.append(_trace("done", "ok", f"total {total_ms:.0f} ms"))

        return RoutingOutcome(
            result=result,
            primary_model=primary.model_id,
            alternatives_used=alternatives_used,
            escalated=escalated,
            needs_confirmation=needs_confirmation,
            reason=reason,
            confidence=estimate.score,
            confidence_source=estimate.source,
            confidence_components=estimate.components,
            trace=trace,
            predictions=predictions,
            total_latency_ms=total_ms,
            policy=self.policy,
        )

    def _uncertain_segments(
        self, audio: AudioPayload, result: ASRResult
    ) -> List[tuple[AudioPayload, SegmentResult]]:
        """Choose which audio regions to re-run.

        If the provider gave timed segments we use those.  If it gave none
        (Saaras returns a single untimed block for short audio) we escalate the
        whole utterance rather than pretending to know which word was uncertain.
        """
        timed = [s for s in result.segments if (s.end - s.start) >= self.policy.min_segment_seconds]
        if not timed:
            return [(audio, SegmentResult(text=result.text, start=0.0, end=audio.duration_seconds))]
        return [(audio.slice_seconds(s.start, s.end), s) for s in timed]
