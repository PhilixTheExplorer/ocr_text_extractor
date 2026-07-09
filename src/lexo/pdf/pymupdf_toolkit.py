"""PDF operations backed by PyMuPDF. Implements the `PdfToolkit` port.

Pure document manipulation - no OCR. Crop/split/extract here also improve OCR
accuracy later (e.g. trimming headers/footers before recognition).
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pymupdf

from lexo.domain.models import (
    CropBox,
    DocumentInfo,
    DocumentKind,
    PageImage,
    PageText,
    TextKind,
)
from lexo.domain.ranges import PageRanges
from lexo.infra.hashing import sha256_file

# Google Docs OCR rejects very large uploads (HTTP 413) and silently returns no
# text for over-large images. Cap the rendered page's longest edge so a page of
# any physical size stays within those limits; OCR accuracy is unaffected at this
# resolution. A point is 1/72 inch, so pixels = points / 72 * dpi.
_MAX_OCR_EDGE_PX = 3500
_OCR_JPEG_QUALITY = 85

# Fraction of visible characters that must be Private Use Area glyphs before a
# text layer is judged unusable. Real documents never approach this; legacy
# non-Unicode fonts produce text that is almost entirely PUA.
_PUA_JUNK_THRESHOLD = 0.5


def _is_pua(codepoint: int) -> bool:
    return (
        0xE000 <= codepoint <= 0xF8FF  # BMP Private Use Area
        or 0xF0000 <= codepoint <= 0xFFFFD  # Supplementary PUA-A
        or 0x100000 <= codepoint <= 0x10FFFD  # Supplementary PUA-B
    )


def _is_glyph_soup(text: str) -> bool:
    """True if the text layer is mostly Private Use Area glyphs.

    Some legacy fonts (e.g. older Burmese printing fonts) embed a "text layer"
    whose code points are font-specific PUA glyph ids, not Unicode. PyMuPDF reads
    it back as non-empty text, but it is meaningless and renders as tofu, so the
    page must be OCR'd as if it had no text layer at all."""
    visible = [c for c in text if not c.isspace()]
    if not visible:
        return False
    pua = sum(1 for c in visible if _is_pua(ord(c)))
    return pua / len(visible) >= _PUA_JUNK_THRESHOLD


def _ocr_render_dpi(width_pt: float, height_pt: float, dpi: int) -> int:
    """The requested dpi, lowered just enough that the longest rendered edge does
    not exceed _MAX_OCR_EDGE_PX."""
    longest_pt = max(width_pt, height_pt)
    if longest_pt <= 0:
        return dpi
    max_dpi = _MAX_OCR_EDGE_PX * 72.0 / longest_pt
    return max(1, min(dpi, int(max_dpi)))


class PyMuPdfToolkit:
    def page_count(self, pdf: Path) -> int:
        doc = pymupdf.open(pdf)
        try:
            return doc.page_count
        finally:
            doc.close()

    def inspect(self, pdf: Path) -> DocumentInfo:
        doc = pymupdf.open(pdf)
        try:
            sizes: list[tuple[float, float]] = []
            has_text = False
            for i in range(doc.page_count):
                page = doc[i]
                rect = page.rect
                sizes.append((rect.width, rect.height))
                if not has_text and page.get_text("text").strip():
                    has_text = True
            return DocumentInfo(
                kind=DocumentKind.PDF,
                page_count=doc.page_count,
                has_text_layer=has_text,
                page_sizes=sizes,
            )
        finally:
            doc.close()

    def extract_pages(self, pdf: Path, ranges: PageRanges, out: Path) -> Path:
        doc = pymupdf.open(pdf)
        try:
            indices = ranges.resolve(doc.page_count)
            if not indices:
                raise ValueError("no pages selected")
            doc.select(indices)
            out.parent.mkdir(parents=True, exist_ok=True)
            doc.save(out)
            return out
        finally:
            doc.close()

    def reorder(self, pdf: Path, order: list[int], out: Path) -> Path:
        doc = pymupdf.open(pdf)
        try:
            if sorted(order) != list(range(doc.page_count)):
                raise ValueError("reorder needs a permutation of all page indices")
            # select() keeps the given order, unlike extract_pages which sorts.
            doc.select(order)
            out.parent.mkdir(parents=True, exist_ok=True)
            doc.save(out)
            return out
        finally:
            doc.close()

    def split(
        self,
        pdf: Path,
        *,
        every: int | None = None,
        at: list[int] | None = None,
        out_dir: Path | None = None,
    ) -> list[Path]:
        if (every is None) == (at is None):
            raise ValueError("provide exactly one of `every` or `at`")
        src = pymupdf.open(pdf)
        try:
            chunks = self._chunks(src.page_count, every, at)
            target = out_dir or pdf.parent
            target.mkdir(parents=True, exist_ok=True)
            outputs: list[Path] = []
            for idx, (start, end) in enumerate(chunks, 1):
                dst = pymupdf.open()
                dst.insert_pdf(src, from_page=start, to_page=end)
                outpath = target / f"{pdf.stem}_part{idx:03d}.pdf"
                dst.save(outpath)
                dst.close()
                outputs.append(outpath)
            return outputs
        finally:
            src.close()

    @staticmethod
    def _chunks(n: int, every: int | None, at: list[int] | None) -> list[tuple[int, int]]:
        if n == 0:
            return []
        if every is not None:
            if every < 1:
                raise ValueError("`every` must be >= 1")
            return [(s, min(s + every, n) - 1) for s in range(0, n, every)]
        cuts = sorted({p - 1 for p in (at or []) if 1 < p <= n})
        starts = [0, *cuts]
        ends = [c - 1 for c in cuts] + [n - 1]
        return list(zip(starts, ends, strict=True))

    def crop(self, pdf: Path, box: CropBox, out: Path, ranges: PageRanges | None = None) -> Path:
        doc = pymupdf.open(pdf)
        try:
            selected = set(ranges.resolve(doc.page_count)) if ranges else set(range(doc.page_count))
            for i in range(doc.page_count):
                if i not in selected:
                    continue
                page = doc[i]
                if box.relative:
                    # cropbox, not page.rect: set_cropbox wants mediabox-relative
                    # coords, so a second crop insets the visible region.
                    r = page.cropbox
                    new = pymupdf.Rect(
                        r.x0 + box.left * r.width,
                        r.y0 + box.top * r.height,
                        r.x0 + box.right * r.width,
                        r.y0 + box.bottom * r.height,
                    )
                else:
                    new = pymupdf.Rect(box.left, box.top, box.right, box.bottom)
                page.set_cropbox(new)
            out.parent.mkdir(parents=True, exist_ok=True)
            doc.save(out)
            return out
        finally:
            doc.close()

    def rotate(self, pdf: Path, degrees: int, out: Path, ranges: PageRanges | None = None) -> Path:
        if degrees % 90 != 0:
            raise ValueError("degrees must be a multiple of 90")
        doc = pymupdf.open(pdf)
        try:
            selected = set(ranges.resolve(doc.page_count)) if ranges else set(range(doc.page_count))
            for i in range(doc.page_count):
                if i in selected:
                    page = doc[i]
                    page.set_rotation((page.rotation + degrees) % 360)
            out.parent.mkdir(parents=True, exist_ok=True)
            doc.save(out)
            return out
        finally:
            doc.close()

    def merge(self, pdfs: list[Path], out: Path) -> Path:
        if not pdfs:
            raise ValueError("no input PDFs to merge")
        dst = pymupdf.open()
        try:
            for p in pdfs:
                src = pymupdf.open(p)
                dst.insert_pdf(src)
                src.close()
            out.parent.mkdir(parents=True, exist_ok=True)
            dst.save(out)
            return out
        finally:
            dst.close()

    def split_spreads(self, pdf: Path, out: Path, ratio: float = 0.5) -> Path:
        # Split each two-up page into two pages, left half then right half.
        if not 0.05 <= ratio <= 0.95:
            raise ValueError("ratio must be between 0.05 and 0.95")
        src = pymupdf.open(pdf)
        try:
            dst = pymupdf.open()
            for i in range(src.page_count):
                page = src[i]
                # Split page.rect (the displayed box) so halves match what the user
                # sees, then inset the copy's cropbox. set_cropbox wants unrotated
                # mediabox coords and page.rect sits at the origin, so shift each
                # half by the current cropbox's rotated offset before derotating -
                # else a re-split crops from the mediabox origin, duplicating halves.
                r = page.rect
                mid = r.x0 + r.width * ratio
                halves = (
                    pymupdf.Rect(r.x0, r.y0, mid, r.y1),
                    pymupdf.Rect(mid, r.y0, r.x1, r.y1),
                )
                cropbox_rot = pymupdf.Rect(page.cropbox) * page.rotation_matrix
                cropbox_rot.normalize()
                to_origin = pymupdf.Matrix(1, 0, 0, 1, cropbox_rot.x0, cropbox_rot.y0)
                for disp in halves:
                    dst.insert_pdf(src, from_page=i, to_page=i)
                    box = pymupdf.Rect(disp * to_origin * page.derotation_matrix)
                    box.normalize()
                    dst[-1].set_cropbox(box)
            out.parent.mkdir(parents=True, exist_ok=True)
            dst.save(out)
            dst.close()
            return out
        finally:
            src.close()

    def render(
        self, pdf: Path, ranges: PageRanges, dpi: int = 300, doc_id: str | None = None
    ) -> Iterator[PageImage]:
        doc = pymupdf.open(pdf)
        try:
            # Hashing the whole file is expensive on large PDFs; let a caller that
            # already knows the id (e.g. a batched run) pass it in to avoid
            # re-hashing on every batch.
            doc_id = doc_id if doc_id is not None else sha256_file(pdf)
            for i in ranges.resolve(doc.page_count):
                page = doc[i]
                eff_dpi = _ocr_render_dpi(page.rect.width, page.rect.height, dpi)
                pix = page.get_pixmap(dpi=eff_dpi)
                # JPEG, not PNG: scanned/photographic pages barely compress as PNG
                # (tens of MB), which both blows past Drive's upload limit and
                # exceeds what Google's OCR will process - it returns empty text.
                # A capped-resolution JPEG stays small and OCRs identically.
                yield PageImage(
                    doc_id=doc_id,
                    index=i,
                    image_bytes=pix.tobytes("jpg", jpg_quality=_OCR_JPEG_QUALITY),
                    dpi=eff_dpi,
                    mimetype="image/jpeg",
                )
        finally:
            doc.close()

    def extract_text_layer(
        self, pdf: Path, ranges: PageRanges, *, detect_scanned: bool = False
    ) -> list[PageText]:
        doc = pymupdf.open(pdf)
        try:
            pages: list[PageText] = []
            for i in ranges.resolve(doc.page_count):
                page = doc[i]
                text = page.get_text("text")
                if not text.strip():
                    kind = TextKind.SCANNED
                elif _is_glyph_soup(text):
                    # A legacy non-Unicode font's glyph soup is no better than
                    # no text layer: drop it and let OCR produce real text.
                    text, kind = "", TextKind.SCANNED
                elif detect_scanned and self._is_image_page(page):
                    # A full-page image with a thin text layer is a scan whose
                    # embedded text is often wrong or in the wrong script; OCR it.
                    kind = TextKind.SCANNED
                else:
                    kind = TextKind.DIGITAL
                pages.append(PageText(index=i, text=text, kind=kind))
            return pages
        finally:
            doc.close()

    @staticmethod
    def _is_image_page(page: pymupdf.Page, coverage: float = 0.8) -> bool:
        """True if a single image covers most of the page (a scanned page)."""
        page_area = page.rect.width * page.rect.height
        if page_area <= 0:
            return False
        try:
            infos = page.get_image_info()
        except Exception:
            return False
        for info in infos:
            bbox = info.get("bbox")
            if not bbox:
                continue
            x0, y0, x1, y1 = bbox
            if abs((x1 - x0) * (y1 - y0)) / page_area >= coverage:
                return True
        return False
