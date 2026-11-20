from __future__ import annotations


def test_vocabulary_crud(client, headers):
    created = client.post("/api/vocabulary", headers=headers, json={
        "word": "naresh", "preferred_spelling": "Naresh", "category": "personal_name",
        "language_code": "en-IN"})
    assert created.status_code == 201, created.text
    entry_id = created.json()["id"]

    listed = client.get("/api/vocabulary", headers=headers)
    assert listed.status_code == 200
    assert any(e["id"] == entry_id for e in listed.json())

    updated = client.put(f"/api/vocabulary/{entry_id}", headers=headers,
                         json={"category": "technical", "weight": 2.0})
    assert updated.status_code == 200
    assert updated.json()["category"] == "technical"

    deleted = client.delete(f"/api/vocabulary/{entry_id}", headers=headers)
    assert deleted.status_code == 204
    assert client.get("/api/vocabulary", headers=headers).json() == []


def test_duplicate_entry_conflict(client, headers):
    payload = {"word": "bharatvoice", "preferred_spelling": "BharatVoice", "language_code": "en-IN"}
    assert client.post("/api/vocabulary", headers=headers, json=payload).status_code == 201
    assert client.post("/api/vocabulary", headers=headers, json=payload).status_code == 409


def test_bulk_import_and_export(client, headers):
    resp = client.post("/api/vocabulary/import", headers=headers, json={"entries": [
        {"word": "cit", "preferred_spelling": "CIT", "category": "acronym", "language_code": "en-IN"},
        {"word": "chennai", "preferred_spelling": "Chennai", "category": "place", "language_code": "en-IN"},
    ]})
    assert resp.status_code == 200
    assert resp.json()["created"] == 2

    export = client.get("/api/vocabulary/export?fmt=json", headers=headers)
    assert export.status_code == 200
    assert "CIT" in export.text

    csv_export = client.get("/api/vocabulary/export?fmt=csv", headers=headers)
    assert csv_export.status_code == 200
    assert "preferred_spelling" in csv_export.text


def test_search_filter(client, headers):
    client.post("/api/vocabulary", headers=headers, json={
        "word": "fastapi", "preferred_spelling": "FastAPI", "category": "technical"})
    found = client.get("/api/vocabulary?search=fast", headers=headers)
    assert found.status_code == 200
    assert len(found.json()) == 1
    empty = client.get("/api/vocabulary?search=zzzz", headers=headers)
    assert empty.json() == []


def test_cannot_touch_other_users_entry(client, headers):
    entry = client.post("/api/vocabulary", headers=headers, json={
        "word": "private", "preferred_spelling": "Private"}).json()
    other = client.post("/api/auth/register", json={
        "email": "other@example.com", "password": "password1234"}).json()
    other_headers = {"Authorization": f"Bearer {other['access_token']}"}
    assert client.delete(f"/api/vocabulary/{entry['id']}", headers=other_headers).status_code == 404
