from __future__ import annotations


def test_health(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_register_login_me(client):
    reg = client.post("/api/auth/register", json={
        "email": "asha@example.com", "password": "password1234", "full_name": "Asha"})
    assert reg.status_code == 201
    token = reg.json()["access_token"]

    me = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    assert me.json()["email"] == "asha@example.com"

    login = client.post("/api/auth/login", json={"email": "asha@example.com", "password": "password1234"})
    assert login.status_code == 200
    assert login.json()["token_type"] == "bearer"


def test_duplicate_email_rejected(client, auth):
    resp = client.post("/api/auth/register", json={
        "email": auth["email"], "password": "anotherpass123"})
    assert resp.status_code == 409


def test_wrong_password(client, auth):
    resp = client.post("/api/auth/login", json={"email": auth["email"], "password": "wrongpass123"})
    assert resp.status_code == 401


def test_validation_rejects_short_password(client):
    resp = client.post("/api/auth/register", json={"email": "x@example.com", "password": "short"})
    assert resp.status_code == 422


def test_protected_route_requires_token(client):
    assert client.get("/api/auth/me").status_code == 401
    assert client.get("/api/auth/me", headers={"Authorization": "Bearer nonsense"}).status_code == 401


def test_refresh_token_flow(client, auth):
    resp = client.post("/api/auth/refresh", json={"refresh_token": auth["refresh"]})
    assert resp.status_code == 200
    assert resp.json()["access_token"]


def test_refresh_token_cannot_be_used_as_access(client, auth):
    resp = client.get("/api/auth/me", headers={"Authorization": f"Bearer {auth['refresh']}"})
    assert resp.status_code == 401
