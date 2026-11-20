"""Application settings.  Every secret lives here, on the backend only."""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import List, Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parent.parent
REPO_ROOT = BACKEND_DIR.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(REPO_ROOT / ".env", BACKEND_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # --- app ---
    app_name: str = "BharatVoice AI"
    environment: str = "development"
    debug: bool = True
    secret_key: str = "dev-only-insecure-secret-change-me-please-32b"
    access_token_expire_minutes: int = 60
    refresh_token_expire_days: int = 14
    cors_origins: List[str] = Field(default_factory=lambda: ["http://localhost:5173"])
    public_base_url: str = "http://localhost:8000"

    # --- database ---
    database_url: str = "sqlite:///./bharatvoice.db"
    db_echo: bool = False

    # --- cache ---
    redis_url: Optional[str] = None
    cache_enabled: bool = False

    # --- sarvam (primary ASR) ---
    sarvam_api_key: Optional[str] = None
    sarvam_base_url: str = "https://api.sarvam.ai"
    sarvam_stt_path: str = "/speech-to-text"
    sarvam_realtime_ws_url: str = "wss://api.sarvam.ai/speech-to-text-realtime/ws"
    sarvam_model: str = "saaras:v4"
    sarvam_timeout_seconds: float = 45.0
    sarvam_max_retries: int = 2
    sarvam_monthly_request_budget: int = 20000

    # --- alternative asr ---
    whisper_enabled: bool = False
    whisper_model: str = "small"
    whisper_device: str = "cpu"
    whisper_compute_type: str = "int8"
    indicconformer_enabled: bool = False
    indicconformer_model_dir: str = "./models/indicconformer"

    # --- multilingual ---
    indictrans2_enabled: bool = False
    indictrans2_model_dir: str = "./models/indictrans2"
    indicxlit_enabled: bool = False
    indicxlit_model_dir: str = "./models/indicxlit"
    deepfilternet_enabled: bool = False
    silero_vad_enabled: bool = False
    silero_vad_model_path: str = "./models/silero_vad.onnx"

    # --- demo / limits ---
    demo_mode: bool = True
    max_upload_mb: int = 25
    max_recording_seconds: int = 300
    rate_limit_transcribe_per_minute: int = 30
    audio_retention_default: str = "discard"

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _split_origins(cls, v):
        if isinstance(v, str):
            return [o.strip() for o in v.split(",") if o.strip()]
        return v

    @property
    def is_production(self) -> bool:
        return self.environment.lower() == "production"

    @property
    def sarvam_configured(self) -> bool:
        return bool(self.sarvam_api_key and self.sarvam_api_key.strip())


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
