"""Per-page routing: use the embedded text layer when present, OCR otherwise.

A digital PDF page already has perfect text, so OCR is skipped (faster and
lossless). Scanned pages are rendered to images and sent to the engine. Mixed
documents are handled page by page. force_ocr overrides for bad text layers.
"""

from __future__ import annotations

import hashlib
import io
import uuid
from collections.abc import Callable
from dataclasses import dataclass, replace
from pathlib import Path

from lexo.domain.events import Event, PageCompleted, RunCancelled, RunCompleted, RunStarted
from lexo.domain.models import ExtractedDoc, OcrResult, PageImage, PageText, TextKind
from lexo.domain.ranges import PageRanges
from lexo.infra.hashing import sha256_file
from lexo.pipeline.engine import CancellationToken, Cancelled, OcrEngine
from lexo.ports.pdf_toolkit import PdfToolkit

Postprocessor = Callable[[str], str]
EventSink = Callable[[Event], None]


def _postprocessing_sink(
    on_event: EventSink | None, postprocessor: Postprocessor | None
) -> EventSink | None:
    """Wrap a sink so each PageCompleted carries post-processed text, matching the
    text the router stores for export. Other events pass through untouched."""
    if on_event is None or postprocessor is None:
        return on_event

    def sink(event: Event) -> None:
        if isinstance(event, PageCompleted):
            event = replace(event, text=postprocessor(event.text))
        on_event(event)

    return sink


@dataclass
class OcrRouter:
    toolkit: PdfToolkit
    engine: OcrEngine
    dpi: int = 300
    # Pages are rendered and OCR'd in batches of this size so a large document
    # never holds all of its page images in memory at once.
    batch_size: int = 8

    async def process_pdf(
        self,
        pdf: Path,
        ranges: PageRanges | None = None,
        *,
        lang: str | None = None,
        force_ocr: bool = False,
        postprocessor: Postprocessor | None = None,
        on_event: EventSink | None = None,
        token: CancellationToken | None = None,
    ) -> ExtractedDoc:
        page_count = self.toolkit.page_count(pdf)
        text_pages = self.toolkit.extract_text_layer(
            pdf, ranges or PageRanges.all_pages(), detect_scanned=True
        )

        need_ocr = [
            pt.index
            for pt in text_pages
            if force_ocr or pt.kind != TextKind.DIGITAL or not pt.text.strip()
        ]

        ocr_results: dict[int, OcrResult] = {}
        ocr_failures: dict[int, str] = {}
        if need_ocr:
            ocr_results, ocr_failures = await self._ocr_in_batches(
                pdf,
                need_ocr,
                lang=lang,
                on_event=_postprocessing_sink(on_event, postprocessor),
                token=token,
            )

        pages: list[PageText] = []
        for pt in text_pages:
            if pt.index in ocr_results:
                text, kind = ocr_results[pt.index].text, TextKind.SCANNED
                error = None
            elif pt.index in ocr_failures:
                text, kind = "", TextKind.FAILED
                error = ocr_failures[pt.index]
            else:
                text, kind = pt.text, pt.kind
                error = pt.error
            if postprocessor is not None:
                text = postprocessor(text)
            pages.append(PageText(index=pt.index, text=text, kind=kind, error=error))

        return ExtractedDoc(
            doc_id=sha256_file(pdf),
            source_name=pdf.name,
            page_count=page_count,
            pages=pages,
        )

    async def _ocr_in_batches(
        self,
        pdf: Path,
        need_ocr: list[int],
        *,
        lang: str | None,
        on_event: EventSink | None,
        token: CancellationToken | None,
    ) -> tuple[dict[int, OcrResult], dict[int, str]]:
        """Render and OCR `need_ocr` pages in fixed-size batches, emitting a single
        run's worth of lifecycle events across all batches."""
        emit = on_event or (lambda _event: None)
        rid = uuid.uuid4().hex
        size = max(1, self.batch_size, self.engine.concurrency)
        results: dict[int, OcrResult] = {}
        failures: dict[int, str] = {}

        emit(RunStarted(run_id=rid, pages_total=len(need_ocr)))
        try:
            for start in range(0, len(need_ocr), size):
                chunk = need_ocr[start : start + size]
                spec = ",".join(str(i + 1) for i in chunk)
                images = list(self.toolkit.render(pdf, PageRanges.parse(spec), dpi=self.dpi))
                run = await self.engine.run(
                    images,
                    lang=lang,
                    on_event=on_event,
                    token=token,
                    run_id=rid,
                    emit_lifecycle=False,
                )
                results.update(run.results)
                failures.update(run.failures)
        except Cancelled:
            emit(RunCancelled(run_id=rid))
            raise
        emit(RunCompleted(run_id=rid, pages_done=len(results)))
        return results, failures

    async def process_image(
        self,
        path: Path,
        *,
        lang: str | None = None,
        postprocessor: Postprocessor | None = None,
        on_event: EventSink | None = None,
        token: CancellationToken | None = None,
    ) -> ExtractedDoc:
        from PIL import Image

        with Image.open(path) as image:
            buffer = io.BytesIO()
            image.save(buffer, format="PNG")
        doc_id = sha256_file(path)
        page_image = PageImage(doc_id=doc_id, index=0, image_bytes=buffer.getvalue(), dpi=self.dpi)
        run = await self.engine.run(
            [page_image],
            lang=lang,
            on_event=_postprocessing_sink(on_event, postprocessor),
            token=token,
        )
        result = run.results.get(0)
        text = result.text if result is not None else ""
        if postprocessor is not None:
            text = postprocessor(text)
        kind = TextKind.FAILED if 0 in run.failures else TextKind.SCANNED
        return ExtractedDoc(
            doc_id=doc_id,
            source_name=path.name,
            page_count=1,
            pages=[PageText(index=0, text=text, kind=kind, error=run.failures.get(0))],
        )

    async def process_images(
        self,
        paths: list[Path],
        ranges: PageRanges | None = None,
        *,
        lang: str | None = None,
        postprocessor: Postprocessor | None = None,
        on_event: EventSink | None = None,
        token: CancellationToken | None = None,
    ) -> ExtractedDoc:
        from PIL import Image

        page_count = len(paths)
        indexes = ranges.resolve(page_count) if ranges is not None else list(range(page_count))
        doc_id = _hash_files(paths)
        images: list[PageImage] = []
        for index in indexes:
            with Image.open(paths[index]) as image:
                buffer = io.BytesIO()
                image.save(buffer, format="PNG")
            images.append(
                PageImage(doc_id=doc_id, index=index, image_bytes=buffer.getvalue(), dpi=self.dpi)
            )
        run = await self.engine.run(
            images,
            lang=lang,
            on_event=_postprocessing_sink(on_event, postprocessor),
            token=token,
        )
        pages: list[PageText] = []
        for index in indexes:
            result = run.results.get(index)
            text = result.text if result is not None else ""
            if postprocessor is not None:
                text = postprocessor(text)
            kind = TextKind.FAILED if index in run.failures else TextKind.SCANNED
            pages.append(PageText(index=index, text=text, kind=kind, error=run.failures.get(index)))
        return ExtractedDoc(
            doc_id=doc_id,
            source_name=paths[0].name if paths else "image set",
            page_count=page_count,
            pages=pages,
        )


def _hash_files(paths: list[Path]) -> str:
    digest = hashlib.sha256()
    for path in paths:
        digest.update(path.name.encode("utf-8"))
        digest.update(b"\0")
        with path.open("rb") as file:
            for chunk in iter(lambda: file.read(1024 * 1024), b""):
                digest.update(chunk)
        digest.update(b"\0")
    return digest.hexdigest()
