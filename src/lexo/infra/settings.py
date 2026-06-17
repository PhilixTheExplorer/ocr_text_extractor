"""Runtime configuration. Override via env (``LEXO_*``) or a ``.env`` file."""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="LEXO_", env_file=".env", extra="ignore")

    # OCR
    default_provider: str = "google"
    ocr_language: str = "my"  # Burmese by default
    render_dpi: int = 300
    concurrency: int = 4
    ocr_batch_size: int = 8  # pages rendered+OCR'd at once, to bound memory

    # Logging
    log_level: str = "INFO"


def load_settings() -> Settings:
    return Settings()
