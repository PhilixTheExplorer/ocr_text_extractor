"""Running extract/OCR in the background and reflecting progress.

A mixin of `MainWindow`. Owns the worker lifecycle and translates worker signals
into page-status and progress updates.
"""

from __future__ import annotations

from dataclasses import replace

from lexo.domain.events import (
    Event,
    PageCompleted,
    PageFailed,
    PageStarted,
    RunCompleted,
    RunStarted,
)
from lexo.domain.models import ExtractedDoc, TextKind
from lexo.domain.ranges import PageRanges
from lexo.gui.qt import QMessageBox
from lexo.gui.worker import ProcessWorker
from lexo.pipeline.engine import CancellationToken


class RunMixin:
    def run_process(self) -> None:
        if self.document is None or self.page_count == 0 or self.worker is not None:
            return
        self._save_current_text()
        mode = self._selected_mode_value()
        if mode == "extract" and not self.document.is_pdf:
            QMessageBox.warning(self, "Mode", "Text-layer extraction only works on PDFs.")
            return
        path = (
            self.document.work_images
            if self.document.is_image_set
            else self.document.ocr_path(self.current)
        )
        try:
            ranges = PageRanges.parse(self.pages_field.text()) if self.pages_field.text() else None
        except ValueError as exc:
            QMessageBox.warning(self, "Pages", str(exc))
            return
        self.token = CancellationToken()
        # Google Docs OCR mode always re-OCRs the selected pages (that is what the user
        # picked it for); force_ocr is ignored on the extract path.
        self.worker = ProcessWorker(
            self.service,
            path,
            mode,
            ranges,
            self.token,
            force_ocr=True,
        )
        self.worker.event.connect(self._on_event)
        self.worker.done.connect(self._process_done)
        self.worker.failed.connect(self._process_failed)
        self.worker.cancelled.connect(self._process_cancelled)
        self.run_total = 0
        self.run_done = 0
        self.run_failed = 0
        self.progress.setRange(0, 0)
        self.progress.show()
        self.status.showMessage("Processing…")
        # Indeterminate until the first RunStarted (or until an extract run, which
        # emits no per-page events, finishes).
        self.run_progress.setRange(0, 0)
        self.run_progress_label.setText("Processing…")
        self.worker.start()
        self._refresh()

    def _on_event(self, event: Event) -> None:
        message: str | None = None
        if isinstance(event, RunStarted):
            self.run_total = event.pages_total
            self.run_done = 0
            self.run_failed = 0
            self.progress.setRange(0, max(1, self.run_total))
            self.progress.setValue(0)
            self.run_progress.setRange(0, max(1, self.run_total))
            self.run_progress.setValue(0)
            message = f"Processed 0/{self.run_total} page(s)"
        elif isinstance(event, PageStarted):
            self._set_page_status(event.page_index, "working")
            message = f"Processed {self.run_done + self.run_failed}/{self.run_total} page(s)"
        elif isinstance(event, PageCompleted):
            self.run_done += 1
            # Show the page's result as it lands, instead of only after the whole
            # run finishes. A fresh OCR result supersedes any prior edit.
            self.page_texts[event.page_index] = event.text
            self.edits.pop(event.page_index, None)
            if event.page_index == self.current:
                self.text.blockSignals(True)
                self.text.setPlainText(self.effective_text(event.page_index))
                self.text.blockSignals(False)
            self._set_page_status(event.page_index, "done")
            message = f"Processed {self.run_done + self.run_failed}/{self.run_total} page(s)"
        elif isinstance(event, PageFailed):
            self.run_failed += 1
            self._set_page_status(event.page_index, "failed")
            message = (
                f"Processed {self.run_done + self.run_failed}/{self.run_total} page(s), "
                f"{self.run_failed} failed"
            )
        elif isinstance(event, RunCompleted):
            message = f"OCR complete: {self.run_done}/{self.run_total}"
            if self.run_failed:
                message += f", {self.run_failed} failed"
        done = self.run_done + self.run_failed
        self.progress.setValue(done)
        self.run_progress.setValue(done)
        if message is not None:
            self.status.showMessage(message)
            self.run_progress_label.setText(message)

    def _process_done(self, doc: ExtractedDoc) -> None:
        self.doc = self._merge_run_result(self.doc, doc)
        for page in doc.pages:
            self.page_texts[page.index] = page.text
            self.edits.pop(page.index, None)
            if page.kind == TextKind.FAILED:
                status = "failed"
            elif page.kind == TextKind.DIGITAL:
                status = "text"
            else:
                status = "done"
            self._set_page_status(page.index, status)
        self._finish_worker()
        self.show_page(self.current)
        failed = len(doc.failed_pages)
        ok = len(doc.pages) - failed
        # Extract runs emit no per-page events, so settle the indeterminate bar here.
        self.run_progress.setRange(0, 1)
        self.run_progress.setValue(1)
        summary = f"Done: {ok} page(s)"
        if failed:
            summary += f", {failed} failed (use Retry Failed Pages)"
        self.run_progress_label.setText(summary)
        self.status.showMessage(f"Done: {len(doc.pages)} page(s)")

    @staticmethod
    def _merge_run_result(existing: ExtractedDoc | None, new: ExtractedDoc) -> ExtractedDoc:
        """Overlay a (possibly partial) run onto the previous result for the same
        document, so a partial re-run updates only its pages and leaves the rest
        intact for export. Falls back to the new doc when they don't match."""
        if (
            existing is None
            or existing.doc_id != new.doc_id
            or existing.page_count != new.page_count
        ):
            return new
        by_index = {page.index: page for page in existing.pages}
        for page in new.pages:
            by_index[page.index] = page
        pages = [by_index[index] for index in sorted(by_index)]
        return replace(new, pages=pages)

    def retry_failed_pages(self) -> None:
        if self.worker is not None or self.doc is None:
            return
        failed = self.doc.failed_pages
        if not failed:
            return
        spec = ",".join(str(page.index + 1) for page in failed)
        self.pages_field.setText(spec)
        self.ocr_mode_btn.setChecked(True)
        self.run_process()

    def _process_failed(self, message: str) -> None:
        self._finish_worker()
        self.run_progress.setRange(0, 1)
        self.run_progress.setValue(0)
        self.run_progress_label.setText("Run failed")
        QMessageBox.critical(self, "Run failed", message)
        self.status.showMessage("Run failed")

    def _process_cancelled(self) -> None:
        self._finish_worker()
        self.run_progress.setRange(0, 1)
        self.run_progress.setValue(0)
        done = self.run_done + self.run_failed
        self.run_progress_label.setText(
            f"Cancelled: {done}/{self.run_total} page(s) done" if self.run_total else "Cancelled"
        )
        self.status.showMessage("Cancelled")

    def _finish_worker(self) -> None:
        worker = self.worker
        self.worker = None
        self.token = None
        self._cancelling = False
        self.cancel_act.setText("Cancel")
        self.progress.hide()
        # This runs from the worker's own done/failed/cancelled signal, so its
        # run() has just returned but the QThread may not be fully finished yet.
        # Wait for it before releasing, or Qt aborts with "QThread: Destroyed
        # while thread is still running" (most visible when cancelling mid-run).
        if worker is not None:
            worker.wait()
            worker.deleteLater()
        # A run never changes page count or order, and each page's status badge is
        # already redrawn live via _set_page_status, so there is nothing to rebuild
        # here. Re-rendering every thumbnail (hundreds, on the UI thread) was the
        # end-of-run freeze on large documents. Structural edits still rebuild via
        # their own _reload_pages.
        self.pages.setCurrentRow(self.current)
        self._refresh()

    def cancel_process(self) -> None:
        if self.token is None or self._cancelling:
            return
        self._cancelling = True
        self.token.cancel()
        # Show that the click registered and a stop is in progress: disable the
        # button, relabel it, and spin the bar until the worker actually stops.
        self.cancel_act.setText("Cancelling…")
        self.cancel_act.setEnabled(False)
        self.run_progress.setRange(0, 0)
        self.run_progress_label.setText("Cancelling…")
        self.status.showMessage("Cancelling…")
