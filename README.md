# BharatVoice AI

**Your Voice. Every Indian Language. One Intelligence.**

An adaptive multilingual voice-typing and speech-understanding platform for India's
code-mixed speech. React + TypeScript frontend, FastAPI backend, PostgreSQL, and a
provider-agnostic speech engine that uses **Sarvam AI Saaras v4** as its primary
recogniser with custom routing, code-switch detection and vocabulary adaptation
wrapped around it.

> **Status honesty.** This repository is a working application, not a mockup. What it
> can and cannot do without extra setup is documented precisely in
> [`docs/model_setup.md`](docs/model_setup.md) and
> [`docs/evaluation.md`](docs/evaluation.md). Nothing in the UI fabricates a
> transcript, a confidence score or a metric: unavailable numbers are shown as
> unavailable.

---

## 1. What actually runs

| Capability | Works out of the box | Needs setup |
|---|---|---|
| Landing page, auth, workspace, 9 screens | Yes | — |
| Microphone capture, live waveform, WS streaming | Yes (browser) | — |
| Real Indic ASR via Saaras v4 (transcribe / codemix / translit / translate / verbatim) | — | `SARVAM_API_KEY` |
| Real streaming partials | — | `SARVAM_API_KEY` (realtime WS) |
| Alternative ASR (Whisper / IndicConformer) | — | model install + `*_ENABLED=true` |
| Translation / transliteration via Sarvam | — | `SARVAM_API_KEY` |
| Local IndicTrans2 / IndicXlit | — | model install + flag |
| Code-switch segmentation, routing, vocabulary adaptation | Yes (custom code) | — |
| WER/CER evaluation harness | Yes | reference transcripts you supply |
| Demo fixture transcripts | Yes, **only** with `DEMO_MODE=true`, always badged | — |

With no provider configured the app still runs end to end: it reports
`engine_status: "unavailable"` on `/api/ai/status`, and transcription requests return
HTTP 503 with an actionable message unless demo mode is on.

## 2. Quick start (CPU, ~3 minutes)

```bash
cp .env.example .env                 # add SARVAM_API_KEY for real recognition

# --- backend ---
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload --port 8000

# --- frontend (second terminal) ---
cd frontend
npm install
npm run dev                          # http://localhost:5173
```

Open http://localhost:5173, sign up, and press the microphone.

## 3. Docker

```bash
cp .env.example .env
docker compose up --build           # frontend :5173, API :8000, Postgres :5432
```

## 4. Repository layout

```
bharatvoice-ai/
├── frontend/          React + TS + Vite + Tailwind + Framer Motion + Recharts
├── backend/           FastAPI, SQLAlchemy, JWT, WebSockets, Alembic
├── ai_engine/         Provider adapters + the research modules
├── tauri/             Desktop shell (global shortcut, floating mic)
├── deployment/        Dockerfiles, nginx, compose
├── docs/              architecture, model setup, API, novelty, evaluation
└── scripts/           model install + evaluation runners
```

## 5. Verified in this build

| Check | Command | Result |
|---|---|---|
| Backend unit + integration tests | `cd backend && pytest -q` | **60 passed** (auth, vocabulary, speech, WebSocket live pipeline, engine modules) |
| Frontend type-check + production build | `cd frontend && npm run build` | **passes** (`tsc --noEmit` clean, Vite build ~35 s) |
| Database migrations | `alembic upgrade head` / `downgrade base` | **all 12 tables created and dropped** |
| End-to-end request flow | in-process ASGI run | register → status → transcribe → history → rewrite → analytics → router metrics all 200 |

Screenshots of the running UI: [`docs/screenshots/landing-hero.png`](docs/screenshots/landing-hero.png),
[`docs/screenshots/auth.png`](docs/screenshots/auth.png).

## 6. Documentation

- [docs/architecture.md](docs/architecture.md) — system design and request flow
- [docs/model_setup.md](docs/model_setup.md) — every model, CPU/GPU, download scripts
- [docs/API.md](docs/API.md) — endpoint reference with examples
- [docs/research_novelty.md](docs/research_novelty.md) — what is novel and what is not
- [docs/evaluation.md](docs/evaluation.md) — WER/CER harness and how to report results
- [docs/desktop.md](docs/desktop.md) — Tauri app and its real limitations

## 7. Tests

```bash
cd backend && pytest -q            # API + engine unit tests
cd frontend && npm run build       # type-check + production build
python scripts/run_evaluation.py --manifest eval/sample_manifest.jsonl
```

## 8. Licence / attribution

Model weights (Saaras, IndicConformer, IndicTrans2, IndicXlit, Silero, DeepFilterNet,
Whisper) are governed by their own licences and are **not** vendored here. See
`docs/model_setup.md` for links and licence notes.
