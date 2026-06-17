"""OCR providers and a factory to select one by name."""

from __future__ import annotations

from lexo.ports.ocr_provider import OcrProvider


def get_provider(name: str, lang: str | None = None) -> OcrProvider:
    if name == "google":
        from lexo.providers.google_drive import GoogleDriveOcrProvider

        return GoogleDriveOcrProvider(default_lang=lang or "my")
    raise ValueError(f"unknown provider: {name}")
