"""Core domain models. Pure data - no I/O, no framework imports.

The unit of work is a document (a PDF, an image, or an image set). An image is
just the degenerate one-page case.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum


class DocumentKind(StrEnum):
    PDF = "pdf"
    IMAGE = "image"
    IMAGE_SET = "image_set"


class TextKind(StrEnum):
    DIGITAL = "digital"  # embedded text layer is usable
    SCANNED = "scanned"  # must OCR
    UNKNOWN = "unknown"
    FAILED = "failed"


@dataclass(slots=True)
class PageImage:
    """A rendered or source bitmap ready for OCR."""

    doc_id: str
    index: int
    image_bytes: bytes
    dpi: int = 300
    mimetype: str = "image/png"


@dataclass(slots=True)
class CropBox:
    """Crop region. When `relative`, values are fractions [0, 1] of page size;
    otherwise absolute points."""

    left: float
    top: float
    right: float
    bottom: float
    relative: bool = True


@dataclass(slots=True)
class DocumentInfo:
    """Lightweight result of inspecting a document without a full load."""

    kind: DocumentKind
    page_count: int
    has_text_layer: bool
    page_sizes: list[tuple[float, float]] = field(default_factory=list)


@dataclass(slots=True)
class OcrResult:
    """Plain OCR output for a single page."""

    text: str
    confidence: float = 0.0


@dataclass(slots=True)
class PageText:
    """Text extracted from a single page."""

    index: int  # 0-based
    text: str
    kind: TextKind
    error: str | None = None


@dataclass(slots=True)
class ExtractedDoc:
    """Result of extracting text from a document (a subset of pages may be given)."""

    doc_id: str  # sha256 of source bytes
    source_name: str
    page_count: int  # full document page count
    pages: list[PageText]  # extracted pages (possibly a subset)

    @property
    def has_text(self) -> bool:
        return any(p.kind == TextKind.DIGITAL and p.text.strip() for p in self.pages)

    @property
    def failed_pages(self) -> list[PageText]:
        return [p for p in self.pages if p.kind == TextKind.FAILED]
