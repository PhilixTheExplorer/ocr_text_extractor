"""Background thread for page edits (delete, rotate, crop, split, append).

These operations re-save the working PDF, re-scan its text, and re-render every
thumbnail. On a large document that is seconds of work, so running it on the UI
thread freezes the window. This worker does it off-thread and reports the new
page model and pre-rendered thumbnails back through Qt signals.

PyMuPDF is not thread-safe, so while this worker runs the UI must not render any
page itself (the page strip is disabled and no preview is drawn). The worker is
therefore the only PyMuPDF user for the duration of the edit.
"""

from __future__ import annotations

import base64
from collections.abc import Callable
from dataclasses import dataclass

from lexo.domain.models import PageText
from lexo.gui.document import WorkingDocument
from lexo.gui.qt import QThread, Signal
from lexo.gui.rendering import render_page, render_pdf_page_from_doc

# Matches the size used by the synchronous thumbnail path.
_THUMB_W = 120
_THUMB_H = 160


@dataclass(frozen=True)
class EditResult:
    structural: bool
    page_count: int
    # Fresh page model, only for structural edits (count/order changed);
    # None otherwise, so a rotate/crop keeps existing per-page OCR statuses.
    scan: list[PageText] | None
    # index -> thumbnail PNG bytes (a missing/None value means render failed).
    thumbs: dict[int, bytes | None]


class EditWorker(QThread):
    finished_ok = Signal(object)  # EditResult
    failed = Signal(str)

    def __init__(
        self, document: WorkingDocument, mutation: Callable[[], bool], *, scan: bool = True
    ) -> None:
        super().__init__()
        self.document = document
        self.mutation = mutation
        # A reorder keeps its page model (the GUI remaps it), so it opts out of the
        # rescan; structural edits that change page count keep it on.
        self.scan = scan

    def run(self) -> None:
        try:
            structural = bool(self.mutation())
            doc = self.document
            scan = doc.scan_pages() if (structural and self.scan) else None
            thumbs = self._render_thumbs(doc)
        except Exception as exc:  # pragma: no cover - surfaced through the UI
            self.failed.emit(str(exc))
            return
        self.finished_ok.emit(
            EditResult(
                structural=structural,
                page_count=doc.page_count,
                scan=scan,
                thumbs=thumbs,
            )
        )

    @staticmethod
    def _render_thumbs(doc: WorkingDocument) -> dict[int, bytes | None]:
        thumbs: dict[int, bytes | None] = {}
        if doc.is_pdf:
            import pymupdf

            assert doc.work_path is not None
            pdf = pymupdf.open(doc.work_path)
            try:
                for i in range(doc.page_count):
                    thumbs[i] = _thumb_for_pdf_page(pdf, i)
            finally:
                pdf.close()
        else:
            for i in range(doc.page_count):
                path, kind, render_index = doc.render_target(i)
                try:
                    b64, _, _ = render_page(path, kind, _THUMB_W, _THUMB_H, render_index)
                    thumbs[i] = base64.b64decode(b64)
                except Exception:
                    thumbs[i] = None
        return thumbs


def _thumb_for_pdf_page(pdf: object, index: int) -> bytes | None:
    try:
        b64, _, _ = render_pdf_page_from_doc(pdf, index, _THUMB_W, _THUMB_H)
        return base64.b64decode(b64)
    except Exception:
        return None
