# API reference

Base URL: `http://localhost:8000`. Interactive docs: `/docs`.
All endpoints except `/health`, `/api/system/info` and the auth pair require
`Authorization: Bearer <access_token>`.

## Auth

| Method | Path | Body | Returns |
|---|---|---|---|
| POST | `/api/auth/register` | `{email, password, full_name}` | `{access_token, refresh_token, user}` (201) |
| POST | `/api/auth/login` | `{email, password}` | same |
| POST | `/api/auth/refresh` | `{refresh_token}` | same |
| POST | `/api/auth/logout` | — | 204 |
| GET | `/api/auth/me` | — | `user` |
| POST | `/api/auth/forgot-password` | `{email}` | 202, always the same message |

Refresh tokens carry `typ: "refresh"` and are rejected where an access token is
required.

## Speech

### `POST /api/speech/transcribe` (multipart)

| Field | Type | Default | Notes |
|---|---|---|---|
| `file` | file | — | WAV (pcm_s16le) preferred; other formats need `ffmpeg` |
| `mode` | string | `transcribe` | `transcribe`\|`codemix`\|`translit`\|`translate`\|`verbatim` |
| `context` | string | `general` | `general`\|`email`\|`whatsapp`\|`notes`\|`academic`\|`technical`\|`code` |
| `language_code` | string? | auto | e.g. `ta-IN` |
| `prefer_model` | string? | auto | force a primary adapter |
| `include_outputs` | csv | `native` | subset of `native,romanized,english` |
| `noise_reduction` | bool | false | |
| `retain_audio` | bool | false | stores the WAV |
| `title` | string? | auto | |

Response (abridged):

```json
{
  "id": "3f2a…",
  "text": "Bro inniku college ku late ah varuven because traffic romtha jasthi",
  "mode": "transcribe",
  "primary_language": "ta-IN",
  "languages": ["ta-IN", "en-IN"],
  "is_code_mixed": true,
  "code_switch_count": 4,
  "confidence": 0.62,
  "confidence_source": "proxy",
  "confidence_components": {"audio_quality": 0.81, "lexicon_coverage": 0.43},
  "engine_status": "ok",
  "demo": false,
  "model_used": "saaras:v4",
  "needs_confirmation": false,
  "segments": [{"text": "Bro inniku college ku late ah varuven", "language": "ta-IN", "kind": "matrix", "confidence": 0.7}],
  "outputs": {"native": {"text": "…", "available": true, "method": "asr_native_script"}},
  "routing": {"primary_model": "saaras:v4", "alternatives_used": [], "escalated": false, "trace": []},
  "audio": {"duration_seconds": 4.2, "peak": 0.71, "dbfs": -3.0, "retained": false}
}
```

Errors: `415` undecodable audio, `413` too large/long, `422` bad mode,
`429` rate limited, `503` no recognition backend (with a `hint`).

### `POST /api/speech/upload`
Same pipeline without a socket; no live partials.

### `WS /ws/speech/live?token=<jwt>`

Client → server:
```json
{"type":"start","mode":"transcribe","language_code":"auto","context":"general",
 "include_outputs":["native"],"streaming":true,"sample_rate":16000}
```
then binary frames of mono Int16 PCM, then `{"type":"stop"}` (or `cancel`, `ping`).

Server → client: `ready`, `partial` (only real upstream partials), `final`,
`final_segment`, `vad`, `notice`, `error`, `cancelled`, `pong`.

## Languages

| Method | Path | Notes |
|---|---|---|
| GET | `/api/languages` | reference list with script + support flags |
| GET/POST | `/api/languages/detect` | `{text, base_language}` → `{verdict, code_switching}` |
| POST | `/api/languages/translate` | `{text, source_language, target_language, mode}` |
| POST | `/api/languages/transliterate` | `{text, source_language, target_language}` |

Translate/transliterate return `{text, available, method, reason}`. When
`available` is false, `text` is empty — the original is never passed off as a
translation.

## Vocabulary

`GET /api/vocabulary?search=&category=&language_code=`,
`POST /api/vocabulary`, `PUT /api/vocabulary/{id}`, `DELETE /api/vocabulary/{id}`,
`POST /api/vocabulary/import` `{entries: [...]}`,
`GET /api/vocabulary/export?fmt=json|csv`.

## History

| Method | Path | Notes |
|---|---|---|
| GET | `/api/history?page=&page_size=&search=&language=&sort=&model=` | paginated |
| GET | `/api/history/{id}` | full record with segments |
| PATCH | `/api/history/{id}` | edits; increments `edit_count` |
| POST | `/api/history/{id}/outputs/{native\|romanized\|english}` | generate + store |
| POST | `/api/history/{id}/rewrite?profile=email` | rule-based rewrite |
| DELETE | `/api/history/{id}?hard=false` | soft delete by default |

## Analytics

`GET /api/analytics/overview`, `/languages`, `/performance`,
`/activity?granularity=day|week`. Everything is an aggregate over stored rows;
empty accounts return zeros plus `has_data: false`.

## AI

| Method | Path | Notes |
|---|---|---|
| GET | `/api/ai/models` | adapter availability |
| GET | `/api/ai/status` | primary engine, capabilities, usage meter, notes |
| GET | `/api/ai/router/metrics` | decisions, escalation rate, policy, calibration |
| PUT | `/api/ai/router/policy` | update thresholds live |
| GET | `/api/ai/evaluation` | WER/CER — `available: false` until you run the harness |

## Settings

`GET /api/settings`, `PUT /api/settings`, `PUT /api/settings/profile`,
`DELETE /api/settings/data` (erasure: transcriptions, vocabulary, decisions,
events).

## Errors

```json
{"error": "no_recognition_backend", "message": "router: no recognition backend is available; see /api/ai/status", "hint": "Set SARVAM_API_KEY …"}
```
Validation failures return `{"error":"validation_error","details":[…]}`, and
unhandled errors return a `request_id` you can grep in the server log.
