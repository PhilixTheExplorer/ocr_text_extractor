"""Background processing thread for extract/OCR runs.

Keeps the long-running service call off the UI thread and reports progress,
completion, failure, and cancellation through Qt signals.
"""

from __future__ import annotations

import asyncio
from pathlib import Path

from lexo.gui.qt import QThread, Signal
from lexo.pipeline.engine import CancellationToken, Cancelled
from lexo.services import LexoService


class ProcessWorker(QThread):
    event = Signal(object)
    done = Signal(object)
    failed = Signal(str)
    cancelled = Signal()

    def __init__(
        self,
        service: LexoService,
        path: Path | list[Path],
        mode: str,
        ranges: object,
        token: CancellationToken,
        force_ocr: bool = False,
    ) -> None:
        super().__init__()
        self.service = service
        self.path = path
        self.mode = mode
        self.ranges = ranges
        self.token = token
        self.force_ocr = force_ocr

    def run(self) -> None:
        try:
            if self.mode == "extract":
                doc = self.service.extract(self.path, self.ranges)
            else:
                doc = asyncio.run(
                    self.service.ocr(
                        self.path,
                        provider="google",
                        ranges=self.ranges,
                        force_ocr=self.force_ocr,
                        on_event=lambda event: self.event.emit(event),
                        token=self.token,
                    )
                )
        except Cancelled:
            self.cancelled.emit()
        except Exception as exc:  # pragma: no cover - shown through UI
            self.failed.emit(str(exc))
        else:
            self.done.emit(doc)
