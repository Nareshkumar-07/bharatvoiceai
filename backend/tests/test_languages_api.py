from __future__ import annotations


def test_list_languages(client, headers):
    resp = client.get("/api/languages", headers=headers)
    assert resp.status_code == 200
    codes = {l["code"] for l in resp.json()}
    assert {"ta-IN", "hi-IN", "en-IN", "te-IN"} <= codes


def test_detect_code_mixed(client, headers):
    resp = client.get("/api/languages/detect", params={
        "text": "Tomorrow meeting ku presentation ready pannidu", "base_language": "ta-IN"},
        headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["code_switching"]["is_code_mixed"] is True
    assert body["verdict"]["confidence_source"] == "heuristic"


def test_translate_reports_unavailable_without_key(client, headers):
    resp = client.post("/api/languages/translate", headers=headers,
                       json={"text": "நாளை வருவேன்", "source_language": "ta-IN",
                             "target_language": "en-IN"})
    assert resp.status_code == 200
    body = resp.json()
    # honest: no provider configured in tests
    assert body["available"] is False
    assert body["text"] == ""
    assert body["reason"]


def test_transliterate_reports_unavailable_or_real(client, headers):
    resp = client.post("/api/languages/transliterate", headers=headers,
                       json={"text": "நாளை வருவேன்", "source_language": "ta-IN",
                             "target_language": "en-IN"})
    assert resp.status_code == 200
    body = resp.json()
    assert "available" in body
    if body["available"]:
        assert body["text"]
