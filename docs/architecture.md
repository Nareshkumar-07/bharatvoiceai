# Architecture

```
Browser (React 18 + TS)
  ├─ AudioWorklet ──► Int16 PCM 16 kHz ──► WebSocket /ws/speech/live ─┐
  ├─ AnalyserNode ──► live level + waveform (real mic amplitude)      │
  └─ REST fallback: WAV upload ──► POST /api/speech/transcribe ───────┤
                                                                      ▼
FastAPI backend
  ├─ auth (JWT HS256, scrypt hashing)      ├─ history / vocabulary / analytics
  ├─ speech router ──► speech_service ──► AdaptiveRouter               │
  └─ websocket relay ──► Sarvam realtime WS (partials) ────────────────┤
                                                                      ▼
ai_engine (framework-free, unit-tested)
  ├─ adapters/   sarvam (REST + realtime) · whisper · indicconformer · demo fixture
  ├─ audio/      preprocessing · vad · segmentation · noise_reduction
  ├─ intelligence/ language_detection · code_switch_detection · confidence_calibration
  │                adaptive_router · hypothesis_fusion · vocabulary_adaptation
  │                contextual_correction
  ├─ multilingual/ translation · transliteration · script_conversion
  └─ evaluation/  wer · cer · latency · benchmark
                                                                      ▼
PostgreSQL (SQLite in dev)  + optional Redis
```

## Why the engine is a separate package

`ai_engine/` imports nothing from FastAPI or SQLAlchemy. That buys three things:

1. the router and detectors are unit-testable without a database (see
   `backend/tests/test_engine.py`);
2. the same code can run in the Tauri desktop shell or a CLI batch job;
3. swapping the recognition provider is a registry change
   (`ai_engine/registry.py`), never a frontend change.

## Request flow: a single dictation

1. **Capture.** `useRecorder` opens `getUserMedia`, builds an `AudioContext`, and
   loads an inline `AudioWorkletProcessor`. Frames are downsampled to 16 kHz and
   converted to Int16 PCM. The analyser feeds the UI level meter — the same
   buffer that is being uploaded.
2. **Transport.** The socket opens with the JWT in the query string (browsers
   cannot set headers on a WebSocket). The first control frame is
   `{"type":"start", ...}`; the server replies `ready` with `upstream: true|false`.
3. **Streaming (optional).** With `SARVAM_API_KEY` present the backend opens
   `wss://api.sarvam.ai/speech-to-text-realtime/ws` and pipes frames both ways,
   forwarding real `transcript.partial` events. Without a key the client is told
   plainly that partials are unavailable; nothing is simulated.
4. **Recognition.** On `stop`, either the streamed finals are used (no second
   provider call — cost control) or the buffered PCM goes through the router.
5. **Routing.** `AdaptiveRouter.route()`:
   prepare → select primary → recognise → confidence → (maybe) escalate
   uncertain segments to one alternative → fuse → trace.
6. **Analysis.** `detect_text_language` and `code_switch_detection.analyze`
   attribute a language per token and build spans; `apply_vocabulary` applies
   guarded corrections; `apply_profile` applies the context profile.
7. **Persistence.** `Transcription`, `TranscriptionSegment`, `ModelPrediction`,
   `RoutingDecision`, `RecordingMetadata` and an `AnalyticsEvent` are written in
   one transaction. Audio is written to disk **only** if `retain_audio` was set.
8. **Response.** The UI renders segments, confidence (with its source), the
   routing trace, the audio report and the output tabs.

## Confidence: what is real

| Source | Meaning | Where it comes from |
|---|---|---|
| `provider` | the model's own number | Whisper `avg_logprob` → `exp()` |
| `proxy` | our estimate from observable signals | audio level, lexicon coverage, script coherence, provider language probability, keyterm hits, hypothesis agreement |
| `heuristic` | linguistic heuristic score | token-level script/lexicon attribution |
| `null` | unknown | Saaras returns no token confidence |

`proxy` values are stored with `calibrated: false` until a `Calibrator` is fitted
on labelled evaluation data. The UI shows "proxy estimate (uncalibrated)".

## Database

Twelve tables (see `backend/app/models/`): `users`, `user_preferences`,
`languages`, `transcriptions`, `transcription_segments`, `model_registry`,
`model_predictions`, `routing_decisions`, `user_vocabulary`, `user_corrections`,
`recording_metadata`, `analytics_events`. Indexes cover `user_id`, `created_at`
and the `(user_id, created_at)` pair used by history and analytics. Alembic owns
the schema; `alembic upgrade head` on a fresh database creates all twelve.

## Scaling notes

- The router is stateless; horizontal scaling needs only a shared database.
- Live sessions are per-connection; move the buffer to Redis if you run multiple
  workers behind a load balancer without sticky sessions.
- Analytics are computed with SQL aggregates; add materialised views when a user
  passes ~100k transcriptions.
