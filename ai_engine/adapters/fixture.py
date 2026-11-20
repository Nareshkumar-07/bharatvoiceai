"""Demo fixture adapter - for demos without an API key.

Hard rules:
* Only used when ``DEMO_MODE=true``.
* Every result carries ``demo=True`` and ``engine_status="demo_fixture"``; the API
  stores that flag and the UI renders a "Demo fixture" badge.
* The text is a fixed, hand-written sample.  It is **not** a recognition result
  and must never be shown as one.
"""
from __future__ import annotations

import random
import time
from typing import List, Optional

from ai_engine.base import ASRAdapter, ASRResult, SegmentResult, WordToken

FIXTURES = [
    {
        "id": "ta-en-01",
        "language": "ta-IN",
        "text": "Bro inniku college ku late ah varuven because traffic romba jasthi",
        "segments": [
            ("Bro inniku college ku late ah varuven", "ta-IN"),
            ("because traffic romba jasthi", "ta-IN"),
        ],
    },
    {
        "id": "hi-en-01",
        "language": "hi-IN",
        "text": "Kal meeting hai presentation ready karna hai deadline Friday tak",
        "segments": [
            ("Kal meeting hai presentation ready karna hai", "hi-IN"),
            ("deadline Friday tak", "hi-IN"),
        ],
    },
    {
        "id": "te-en-01",
        "language": "te-IN",
        "text": "Repo ki pull request pampinchu, tests pass ayyayi",
        "segments": [("Repo ki pull request pampinchu", "te-IN"), ("tests pass ayyayi", "te-IN")],
    },
]


class FixtureAdapter(ASRAdapter):
    model_id = "demo-fixture"
    provider = "bharatvoice-demo"
    supports_modes = ("transcribe", "codemix", "translit", "translate", "verbatim")
    returns_confidence = False
    supports_streaming = False
    is_remote = False

    def __init__(self, enabled: bool = True, seed: Optional[int] = None) -> None:
        self.enabled = enabled
        self._rng = random.Random(seed)

    async def is_available(self) -> tuple[bool, Optional[str]]:
        if not self.enabled:
            return False, "DEMO_MODE=false"
        return True, "demo fixture (not a real model)"

    async def transcribe(self, audio, *, mode="transcribe", language_code=None,
                         keyterms=None, context=None) -> ASRResult:
        t0 = time.perf_counter()
        fx = self._rng.choice(FIXTURES)
        segments = [
            SegmentResult(
                text=text,
                start=i * 2.0,
                end=(i + 1) * 2.0,
                language=lang,
                words=[WordToken(text=w) for w in text.split()],
            )
            for i, (text, lang) in enumerate(fx["segments"])
        ]
        text = fx["text"]
        if mode == "translit":
            text = "bro innikku college ku late aa varuven because traffic romba jasthi"
        elif mode == "translate":
            text = "Bro, I will be late to college today because the traffic is very heavy."
        return ASRResult(
            text=text,
            provider=self.provider,
            model=self.model_id,
            mode=mode,
            language=fx["language"],
            language_probability=None,
            segments=segments,
            confidence=None,
            confidence_source=None,
            latency_ms=(time.perf_counter() - t0) * 1000,
            engine_status="demo_fixture",
            demo=True,
            raw={"fixture_id": fx["id"], "note": "DEMO FIXTURE - not a recognition result"},
        )
