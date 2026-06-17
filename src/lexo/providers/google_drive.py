"""Google Docs OCR provider (the primary, free, Burmese-accurate path).

Uploads a page image to Drive as a Google Doc with an OCR language hint, exports
the recognized text, then deletes the temporary file. Uses the drive.file scope,
so it only ever sees files it creates. Sync Drive calls run in a worker thread so
the async engine can process pages concurrently.

Needs Google OAuth (run `lexo login`) and network access, so it is not exercised
in the test suite.
"""

from __future__ import annotations

import asyncio
from typing import Any

from googleapiclient.http import MediaInMemoryUpload

from lexo.domain.models import OcrResult, PageImage

_GOOGLE_DOC = "application/vnd.google-apps.document"
_RETRIES = 2


class GoogleDriveOcrProvider:
    name = "google"
    supports_offline = False

    def __init__(self, service: Any | None = None, default_lang: str = "my") -> None:
        self._service = service
        self.default_lang = default_lang

    def _svc(self) -> Any:
        if self._service is None:
            from lexo.infra.auth_google import build_drive_service

            self._service = build_drive_service()
        return self._service

    async def ocr_page(self, image: PageImage, *, lang: str | None = None) -> OcrResult:
        return await asyncio.to_thread(self._ocr_sync, image, lang or self.default_lang)

    def _ocr_sync(self, image: PageImage, lang: str) -> OcrResult:
        svc = self._svc()
        media = MediaInMemoryUpload(image.image_bytes, mimetype="image/png", resumable=False)
        name = f"lexo-ocr-{image.index}"
        meta = {"name": name, "mimeType": _GOOGLE_DOC}
        created = (
            svc.files()
            .create(body=meta, media_body=media, ocrLanguage=lang, fields="id")
            .execute(num_retries=_RETRIES)
        )
        file_id = created["id"]
        try:
            data = (
                svc.files()
                .export(fileId=file_id, mimeType="text/plain")
                .execute(num_retries=_RETRIES)
            )
            text = data.decode("utf-8") if isinstance(data, bytes) else str(data)
            text = _strip_export_title(text, name)
        finally:
            try:
                svc.files().delete(fileId=file_id).execute(num_retries=_RETRIES)
            except Exception:
                # Best effort cleanup; never fail OCR because delete failed.
                pass
        return OcrResult(text=text, confidence=0.0)

    async def health_check(self) -> bool:
        try:
            await asyncio.to_thread(self._svc)
            return True
        except Exception:
            return False


def _strip_export_title(text: str, title: str) -> str:
    lines = text.splitlines(keepends=True)
    if lines and lines[0].strip() == title:
        return "".join(lines[1:]).lstrip("\r\n")
    return text
