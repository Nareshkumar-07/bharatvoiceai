"""Test bootstrap.

Environment is set BEFORE the app package is imported so the settings singleton
and the SQLAlchemy engine point at a throwaway database.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
REPO_ROOT = BACKEND_DIR.parent
for p in (str(REPO_ROOT), str(BACKEND_DIR)):
    if p not in sys.path:
        sys.path.insert(0, p)

TEST_DB = BACKEND_DIR / "test_bharatvoice.db"
if TEST_DB.exists():
    TEST_DB.unlink()

os.environ.update(
    {
        "DATABASE_URL": f"sqlite:///{TEST_DB}",
        "SARVAM_API_KEY": "",
        "DEMO_MODE": "true",
        "SECRET_KEY": "test-secret-key-for-unit-tests-only-32chars",
        "ENVIRONMENT": "test",
        "ACCESS_TOKEN_EXPIRE_MINUTES": "30",
        "RATE_LIMIT_TRANSCRIBE_PER_MINUTE": "1000",
    }
)

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.database.base import Base  # noqa: E402
from app.database.init_db import seed_reference_data  # noqa: E402
from app.database.session import SessionLocal, engine  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def _schema():
    from app import models  # noqa: F401

    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        seed_reference_data(db)
    yield
    Base.metadata.drop_all(bind=engine)
    if TEST_DB.exists():
        TEST_DB.unlink()


@pytest.fixture()
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture()
def auth(client: TestClient) -> dict:
    import uuid

    email = f"naresh.{uuid.uuid4().hex[:8]}@example.com"
    resp = client.post(
        "/api/auth/register",
        json={"email": email, "password": "supersecret123", "full_name": "Naresh"},
    )
    assert resp.status_code == 201, resp.text
    data = resp.json()
    return {
        "token": data["access_token"],
        "refresh": data["refresh_token"],
        "user": data["user"],
        "email": email,
    }


@pytest.fixture()
def headers(auth: dict) -> dict:
    return {"Authorization": f"Bearer {auth['token']}"}
