"""Adapter registry - the only place that knows which providers exist.

Swapping the recognition provider is a one-line change here; nothing in the API
layer or the frontend names a provider directly.
"""
from __future__ import annotations

import asyncio
from typing import Dict, List, Optional

from ai_engine.adapters.fixture import FixtureAdapter
from ai_engine.adapters.indicconformer.adapter import IndicConformerAdapter
from ai_engine.adapters.sarvam.adapter import SarvamAdapter
from ai_engine.adapters.whisper.adapter import WhisperAdapter
from ai_engine.base import ASRAdapter
from app.config import settings

_adapters: Optional[Dict[str, ASRAdapter]] = None


def build_adapters() -> Dict[str, ASRAdapter]:
    global _adapters
    if _adapters is None:
        adapters: List[ASRAdapter] = [
            SarvamAdapter(),
            WhisperAdapter(),
            IndicConformerAdapter(),
        ]
        if settings.demo_mode:
            adapters.append(FixtureAdapter(enabled=True))
        _adapters = {a.model_id: a for a in adapters}
    return _adapters


def get_adapter(model_id: str) -> ASRAdapter:
    adapters = build_adapters()
    if model_id not in adapters:
        raise KeyError(f"unknown model '{model_id}'")
    return adapters[model_id]


def reset_registry() -> None:
    """Used by tests to rebuild adapters after settings change."""
    global _adapters
    _adapters = None


async def availability_report() -> List[dict]:
    adapters = build_adapters()
    results = await asyncio.gather(
        *[a.is_available() for a in adapters.values()], return_exceptions=True
    )
    report = []
    for adapter, res in zip(adapters.values(), results):
        if isinstance(res, Exception):
            ok, reason = False, f"probe error: {res}"
        else:
            ok, reason = res
        report.append(
            {
                "model_id": adapter.model_id,
                "provider": adapter.provider,
                "available": ok,
                "reason": reason,
                "supports_modes": list(adapter.supports_modes),
                "supports_streaming": adapter.supports_streaming,
                "returns_confidence": adapter.returns_confidence,
                "runtime": "remote-api" if adapter.is_remote else "local",
            }
        )
    return report


async def primary_adapter() -> tuple[Optional[ASRAdapter], Optional[str]]:
    """Return the first available non-demo adapter, or (None, reason)."""
    adapters = build_adapters()
    reasons = []
    for model_id in (settings.sarvam_model, "whisper", "indicconformer"):
        adapter = adapters.get(model_id)
        if adapter is None:
            continue
        ok, reason = await adapter.is_available()
        if ok:
            return adapter, None
        reasons.append(f"{model_id}: {reason}")
    return None, "; ".join(reasons) or "no adapters registered"
