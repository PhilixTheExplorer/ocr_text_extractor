"""Async OCR engine.

Runs a provider over many page images with bounded concurrency, per-page retry,
cooperative cancellation, and a progress event stream. The engine never touches
a UI; callers subscribe via on_event.
"""

from __future__ import annotations

import asyncio
import uuid
from collections.abc import Callable
from dataclasses import dataclass

from lexo.domain.events import (
    Event,
    PageCompleted,
    PageFailed,
    PageStarted,
    RunCancelled,
    RunCompleted,
    RunStarted,
)
from lexo.domain.models import OcrResult, PageImage
from lexo.ports.ocr_provider import OcrProvider

EventSink = Callable[[Event], None]


class Cancelled(Exception):
    """Raised inside the engine when a run is cancelled."""


class CancellationToken:
    def __init__(self) -> None:
        self._cancelled = False

    def cancel(self) -> None:
        self._cancelled = True

    @property
    def cancelled(self) -> bool:
        return self._cancelled

    def check(self) -> None:
        if self._cancelled:
            raise Cancelled


def _noop(_: Event) -> None:
    return None


@dataclass(frozen=True)
class OcrRun:
    results: dict[int, OcrResult]
    failures: dict[int, str]


@dataclass
class OcrEngine:
    provider: OcrProvider
    concurrency: int = 4
    max_retries: int = 3
    retry_base_delay: float = 1.0

    async def run(
        self,
        images: list[PageImage],
        *,
        lang: str | None = None,
        on_event: EventSink | None = None,
        token: CancellationToken | None = None,
        run_id: str | None = None,
        emit_lifecycle: bool = True,
    ) -> OcrRun:
        """Run OCR over `images`. Per-page events are always emitted; the
        RunStarted/RunCompleted/RunCancelled lifecycle events are suppressed when
        `emit_lifecycle` is False, so a batched caller can own a single run."""
        emit = on_event or _noop
        tok = token or CancellationToken()
        rid = run_id or uuid.uuid4().hex
        sem = asyncio.Semaphore(max(1, self.concurrency))
        results: dict[int, OcrResult] = {}
        failures: dict[int, str] = {}

        if emit_lifecycle:
            emit(RunStarted(run_id=rid, pages_total=len(images)))

        async def worker(image: PageImage) -> None:
            async with sem:
                tok.check()
                emit(PageStarted(run_id=rid, page_index=image.index))
                try:
                    res = await self._ocr_with_retry(image, lang, tok)
                except Cancelled:
                    raise
                except Exception as exc:
                    error = str(exc)
                    failures[image.index] = error
                    emit(PageFailed(run_id=rid, page_index=image.index, error=error))
                    return
                results[image.index] = res
                emit(
                    PageCompleted(
                        run_id=rid,
                        page_index=image.index,
                        confidence=res.confidence,
                        text=res.text,
                    )
                )

        tasks = [asyncio.create_task(worker(image)) for image in images]
        try:
            await asyncio.gather(*tasks)
        except Cancelled:
            for task in tasks:
                task.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)
            if emit_lifecycle:
                emit(RunCancelled(run_id=rid))
            raise

        if emit_lifecycle:
            emit(RunCompleted(run_id=rid, pages_done=len(results)))
        return OcrRun(results=results, failures=failures)

    async def _ocr_with_retry(
        self, image: PageImage, lang: str | None, tok: CancellationToken
    ) -> OcrResult:
        last: Exception | None = None
        for attempt in range(self.max_retries):
            tok.check()
            try:
                return await self.provider.ocr_page(image, lang=lang)
            except Cancelled:
                raise
            except Exception as exc:
                last = exc
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(self.retry_base_delay * (attempt + 1))
        assert last is not None
        raise last
