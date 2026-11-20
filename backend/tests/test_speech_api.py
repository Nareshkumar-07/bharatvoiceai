from __future__ import annotations

import io

from tests.helpers import make_wav


def _upload(client, headers, **kwargs):
    data = {"mode": "transcribe", "context": "general", "include_outputs": "native"}
    data.update({k: v for k, v in kwargs.items() if v is not None})
    return client.post(
        "/api/speech/transcribe",
        headers=headers,
        files={"file": ("clip.wav", io.BytesIO(make_wav(2.0)), "audio/wav")},
        data=data,
    )


def test_transcribe_demo_fixture_is_labelled(client, headers):
    resp = _upload(client, headers)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    # no real provider is configured in tests -> fixture path, always badged
    assert body["engine_status"] == "demo_fixture"
    assert body["demo"] is True
    assert body["message"] and "Demo fixture" in body["message"]
    assert body["confidence_source"] in (None, "proxy", "provider")
    assert body["word_count"] > 0
    assert body["routing"]["primary_model"]


def test_transcription_appears_in_history(client, headers):
    created = _upload(client, headers).json()
    page = client.get("/api/history", headers=headers)
    assert page.status_code == 200
    assert page.json()["total"] >= 1
    assert any(item["id"] == created["id"] for item in page.json()["items"])

    detail = client.get(f"/api/history/{created['id']}", headers=headers)
    assert detail.status_code == 200
    assert detail.json()["original_text"] == created["text"]


def test_history_search_and_pagination(client, headers):
    _upload(client, headers, title="Tamil lecture notes")
    found = client.get("/api/history?search=lecture", headers=headers)
    assert found.status_code == 200
    assert found.json()["total"] >= 1
    paged = client.get("/api/history?page=1&page_size=1", headers=headers)
    assert len(paged.json()["items"]) <= 1


def test_edit_transcription_increments_edit_count(client, headers):
    created = _upload(client, headers).json()
    edited = client.patch(f"/api/history/{created['id']}", headers=headers,
                          json={"original_text": "corrected text here"})
    assert edited.status_code == 200
    assert edited.json()["original_text"] == "corrected text here"
    assert edited.json()["edit_count"] == 1


def test_delete_is_soft_then_hidden(client, headers):
    created = _upload(client, headers).json()
    assert client.delete(f"/api/history/{created['id']}", headers=headers).status_code == 204
    assert client.get(f"/api/history/{created['id']}", headers=headers).status_code == 404


def test_unsupported_mode_rejected(client, headers):
    resp = _upload(client, headers, mode="telepathy")
    assert resp.status_code == 422


def test_invalid_audio_rejected(client, headers):
    resp = client.post(
        "/api/speech/transcribe",
        headers=headers,
        files={"file": ("bad.wav", io.BytesIO(b"not audio at all"), "audio/wav")},
        data={"mode": "transcribe"},
    )
    assert resp.status_code == 415


def test_analytics_reflect_real_rows(client, headers):
    _upload(client, headers)
    overview = client.get("/api/analytics/overview", headers=headers)
    assert overview.status_code == 200
    body = overview.json()
    assert body["total_transcriptions"] >= 1
    assert body["total_words"] > 0
    langs = client.get("/api/analytics/languages", headers=headers)
    assert langs.status_code == 200
    perf = client.get("/api/analytics/performance", headers=headers)
    assert perf.status_code == 200
    assert "notes" in perf.json()


def test_settings_roundtrip(client, headers):
    got = client.get("/api/settings", headers=headers)
    assert got.status_code == 200
    updated = client.put("/api/settings", headers=headers,
                         json={"preferred_languages": ["ta-IN", "en-IN"],
                               "default_output_mode": "codemix",
                               "noise_reduction": True})
    assert updated.status_code == 200
    assert updated.json()["default_output_mode"] == "codemix"
    assert updated.json()["noise_reduction"] is True


def test_ai_status_and_metrics(client, headers):
    status = client.get("/api/ai/status", headers=headers)
    assert status.status_code == 200
    body = status.json()
    assert body["primary_engine"] in (None, "saaras:v4")
    assert isinstance(body["models"], list) and body["models"]
    assert "notes" in body

    metrics = client.get("/api/ai/router/metrics", headers=headers)
    assert metrics.status_code == 200
    assert "policy" in metrics.json()

    evaluation = client.get("/api/ai/evaluation", headers=headers)
    assert evaluation.status_code == 200
    assert evaluation.json()["available"] is False
    assert evaluation.json()["wer"] is None


def test_policy_update(client, headers):
    resp = client.put("/api/ai/router/policy", headers=headers,
                      json={"confidence_threshold": 0.6, "max_alternatives": 1})
    assert resp.status_code == 200
    assert resp.json()["policy"]["confidence_threshold"] == 0.6
