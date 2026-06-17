from __future__ import annotations

from lexo.domain.models import OcrResult, PageImage


class FakeProvider:
    """In-memory OcrProvider for tests. Optionally fails the first N attempts."""

    name = "fake"
    supports_offline = True

    def __init__(self, text: str = "OCR", fail_times: int = 0) -> None:
        self.text = text
        self.fail_times = fail_times
        self.calls = 0

    async def ocr_page(self, image: PageImage, *, lang: str | None = None) -> OcrResult:
        self.calls += 1
        if self.calls <= self.fail_times:
            raise RuntimeError("transient failure")
        return OcrResult(text=f"{self.text} p{image.index}", confidence=0.9)

    async def health_check(self) -> bool:
        return True


def make_images(count: int) -> list[PageImage]:
    return [PageImage(doc_id="d", index=i, image_bytes=b"x", dpi=72) for i in range(count)]
