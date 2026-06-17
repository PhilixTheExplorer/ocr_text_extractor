"""Port: text-only OCR, implemented by Google Docs OCR."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from lexo.domain.models import OcrResult, PageImage


@runtime_checkable
class OcrProvider(Protocol):
    name: str
    supports_offline: bool

    async def ocr_page(self, image: PageImage, *, lang: str | None = None) -> OcrResult: ...

    async def health_check(self) -> bool: ...
