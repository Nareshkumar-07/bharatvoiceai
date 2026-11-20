# Model setup

Nothing in this list is vendored in the repository. Every model is opt-in, and
the app reports precisely what is missing instead of degrading silently.

## 1. Sarvam AI Saaras v4 — primary recogniser (remote)

1. Create a key at <https://dashboard.sarvam.ai>.
2. Put it in `.env` on the **backend**:

```bash
SARVAM_API_KEY=sk_...
SARVAM_MODEL=saaras:v4
```

3. Restart the API. `GET /api/ai/status` should now show
   `"primary_engine": "saaras:v4", "primary_available": true`.

What the adapter uses (verified against the public API reference):

| Purpose | Endpoint | Notes |
|---|---|---|
| REST recognition | `POST /speech-to-text` (multipart `file`) | ≤ 30 s per request; the router chunks longer audio at silence boundaries |
| Streaming | `GET /speech-to-text-realtime/ws` | `language_code=auto`, `stream_type`, `mode`, `encoding=linear16`, `sample_rate=16000` |
| Text translation | `POST /translate` | `mayura:v1` (1000 chars) or `sarvam-translate:v1` (2000 chars) |
| Transliteration | `POST /transliterate` | `source_language_code` / `target_language_code` |

Modes implemented: `transcribe`, `codemix`, `translit`, `translate`, `verbatim`.
Keyterm prompting: up to 50 approved vocabulary terms are sent per request.

**Cost control.** `ai_engine/adapters/sarvam/cost.py` keeps a rolling monthly
counter and `SARVAM_MONTHLY_REQUEST_BUDGET` is a soft guard, surfaced on
`GET /api/ai/status`. Streaming is used for live dictation, REST for uploads,
and the realtime path avoids a duplicate REST call on finalisation.

**Confidence.** Saaras does not return token confidence. The adapter leaves
`confidence = null`; the calibration layer supplies a labelled proxy. Do not
"fix" this by inventing a number.

## 2. Whisper (local, optional)

```bash
pip install faster-whisper
# .env
WHISPER_ENABLED=true
WHISPER_MODEL=small          # tiny|base|small|medium|large-v3
WHISPER_DEVICE=cpu           # cpu|cuda
WHISPER_COMPUTE_TYPE=int8    # int8 on CPU, float16 on GPU
```

The first run downloads weights from Hugging Face. Whisper returns
`avg_logprob`, so its confidence is labelled `provider` and is genuinely usable
by the router as an alternative hypothesis source.

## 3. AI4Bharat IndicConformer (local, optional)

```bash
pip install "nemo_toolkit[asr]"
bash scripts/download_models.sh indicconformer   # writes ./models/indicconformer
# .env
INDICCONFORMER_ENABLED=true
INDICCONFORMER_MODEL_DIR=./models/indicconformer
```

Expects `indicconformer_<lang>.nemo` checkpoints (`hi`, `bn`, `ta`, `te`, `gu`,
`kn`, `ml`, `mr`, `pa`, `or`, `as`, `ur`). It needs an explicit language code —
it does not detect one. The adapter refuses to run without it rather than
guessing.

## 4. IndicTrans2 (local translation, optional)

```bash
pip install torch transformers sentencepiece
# download a distilled checkpoint, e.g. ai4bharat/indictrans2-indic-en-dist-200M
INDICTRANS2_ENABLED=true
INDICTRANS2_MODEL_DIR=./models/indictrans2
```

When enabled, local translation is preferred over the API (privacy). The
`IndicTrans2Translator` uses `trust_remote_code=True` checkpoints and needs the
language-tag convention of the checkpoint you downloaded — verify before use.

## 5. IndicXlit / indic-transliteration (optional)

```bash
pip install indic-transliteration     # offline, deterministic, no model download
# or point IndicXlit at a local checkpoint
INDICXLIT_ENABLED=true
INDICXLIT_MODEL_DIR=./models/indicxlit
```

The transliteration service tries Sarvam's API first (better quality), then
`indic-transliteration`, then reports `available: false` with a reason.

## 6. Silero VAD (optional)

```bash
pip install onnxruntime
curl -L -o models/silero_vad.onnx \
  https://github.com/snakers4/silero-vad/raw/master/src/silero_vad/data/silero_vad.onnx
SILERO_VAD_ENABLED=true
```

Without it, `ai_engine/audio/vad.py` uses a frame-energy detector that needs no
downloads.

## 7. DeepFilterNet (optional noise suppression)

```bash
pip install deepfilternet
DEEPFILTERNET_ENABLED=true
```

If the import fails at request time the service falls back to spectral
subtraction and says so (`method: "spectral_gate"`).

## CPU vs GPU

| Component | CPU | GPU |
|---|---|---|
| Saaras v4 | remote (no local compute) | — |
| Whisper small, int8 | ~1–2× realtime on a modern laptop | `WHISPER_DEVICE=cuda`, `float16` |
| IndicConformer | works, slower | recommended |
| IndicTrans2 200M | workable | recommended for batch |

## Verifying what is actually running

```bash
curl -s localhost:8000/api/ai/status -H "Authorization: Bearer $TOKEN" | jq
```

Every model entry carries `available` and, when false, the exact `reason`
(missing key, missing directory, missing Python package). The UI shows the same
data on **AI Intelligence → Module A**.
