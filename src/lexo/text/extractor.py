"""Extract embedded text from digital PDFs.

Pages that already have a text layer are read directly, which is free, instant,
and lossless. Scanned pages come back with empty text and kind SCANNED, to be
OCR'd instead.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import replace
from pathlib import Path

from lexo.domain.models import ExtractedDoc
from lexo.domain.ranges import PageRanges
from lexo.infra.hashing import sha256_file
from lexo.pdf.pymupdf_toolkit import PyMuPdfToolkit
from lexo.pipeline.postprocess import postprocess
from lexo.ports.pdf_toolkit import PdfToolkit

Postprocessor = Callable[[str], str]


class TextExtractor:
    def __init__(
        self, toolkit: PdfToolkit | None = None, postprocessor: Postprocessor | None = postprocess
    ) -> None:
        self.toolkit: PdfToolkit = toolkit or PyMuPdfToolkit()
        self.postprocessor = postprocessor

    def extract(self, pdf: Path, ranges: PageRanges | None = None) -> ExtractedDoc:
        page_count = self.toolkit.page_count(pdf)
        pages = self.toolkit.extract_text_layer(pdf, ranges or PageRanges.all_pages())
        if self.postprocessor is not None:
            pages = [replace(page, text=self.postprocessor(page.text)) for page in pages]
        return ExtractedDoc(
            doc_id=sha256_file(pdf),
            source_name=pdf.name,
            page_count=page_count,
            pages=pages,
        )
