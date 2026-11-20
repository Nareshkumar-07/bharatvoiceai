"""Character error rate."""
from __future__ import annotations

from ai_engine.evaluation.wer import align, normalise


def cer(reference: str, hypothesis: str) -> dict:
    ref = list(normalise(reference).replace(" ", ""))
    hyp = list(normalise(hypothesis).replace(" ", ""))
    stats = align(ref, hyp)
    return {
        "cer": None if not ref else round(stats.errors / len(ref), 4),
        "errors": stats.errors,
        "reference_chars": len(ref),
    }


def corpus_cer(pairs: list[tuple[str, str]]) -> dict:
    total_ref = total_err = 0
    for ref, hyp in pairs:
        ref_chars = list(normalise(ref).replace(" ", ""))
        hyp_chars = list(normalise(hyp).replace(" ", ""))
        total_ref += len(ref_chars)
        total_err += align(ref_chars, hyp_chars).errors
    return {
        "cer": round(total_err / total_ref, 4) if total_ref else None,
        "reference_chars": total_ref,
        "errors": total_err,
        "utterances": len(pairs),
    }
