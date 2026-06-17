"""Port: pure PDF manipulation (no OCR). Implemented on PyMuPDF."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from collections.abc import Iterator
    from pathlib import Path

    from lexo.domain.models import CropBox, DocumentInfo, PageImage, PageText
    from lexo.domain.ranges import PageRanges


@runtime_checkable
class PdfToolkit(Protocol):
    def inspect(self, pdf: Path) -> DocumentInfo: ...

    def page_count(self, pdf: Path) -> int: ...

    def extract_pages(self, pdf: Path, ranges: PageRanges, out: Path) -> Path: ...

    def reorder(self, pdf: Path, order: list[int], out: Path) -> Path: ...

    def split(
        self,
        pdf: Path,
        *,
        every: int | None = None,
        at: list[int] | None = None,
        out_dir: Path | None = None,
    ) -> list[Path]: ...

    def crop(
        self, pdf: Path, box: CropBox, out: Path, ranges: PageRanges | None = None
    ) -> Path: ...

    def rotate(
        self, pdf: Path, degrees: int, out: Path, ranges: PageRanges | None = None
    ) -> Path: ...

    def merge(self, pdfs: list[Path], out: Path) -> Path: ...

    def split_spreads(self, pdf: Path, out: Path, ratio: float = 0.5) -> Path: ...

    def render(self, pdf: Path, ranges: PageRanges, dpi: int = 300) -> Iterator[PageImage]: ...

    def extract_text_layer(
        self, pdf: Path, ranges: PageRanges, *, detect_scanned: bool = False
    ) -> list[PageText]: ...
