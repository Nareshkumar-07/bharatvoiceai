from __future__ import annotations

import time
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.router import api_router
from app.config import settings
from app.core.logging import configure_logging, get_logger
from app.database.init_db import create_all, seed_reference_data
from app.database.session import SessionLocal
from app.middleware.errors import install_error_handlers
from app.websocket.live import router as ws_router

configure_logging()
log = get_logger("backend.main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    if settings.database_url.startswith("sqlite"):
        # convenience for local dev; Alembic remains the source of truth
        create_all()
        with SessionLocal() as db:
            seed_reference_data(db)
    log.info("BharatVoice AI API started (env=%s, demo_mode=%s, sarvam=%s)",
             settings.environment, settings.demo_mode, settings.sarvam_configured)
    yield


app = FastAPI(
    title="BharatVoice AI",
    description="Adaptive multilingual voice intelligence for India's code-mixed speech.",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    openapi_url="/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

install_error_handlers(app)
app.include_router(api_router)
app.include_router(ws_router)


@app.get("/health", tags=["system"])
def health() -> dict:
    return {"status": "ok", "service": settings.app_name, "version": "1.0.0"}


@app.get("/api/system/info", tags=["system"])
def system_info() -> dict:
    return {
        "app": settings.app_name,
        "environment": settings.environment,
        "demo_mode": settings.demo_mode,
        "sarvam_configured": settings.sarvam_configured,
        "streaming": settings.sarvam_configured,
        "max_recording_seconds": settings.max_recording_seconds,
        "max_upload_mb": settings.max_upload_mb,
        "supported_modes": ["transcribe", "codemix", "translit", "translate", "verbatim"],
        "timestamp": int(time.time()),
    }
