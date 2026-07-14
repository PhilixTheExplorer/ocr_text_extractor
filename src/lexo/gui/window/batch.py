"""GUI adapter for multi-PDF batch OCR."""

from __future__ import annotations

from lexo.batch import BatchEvent, BatchOcrConfig, BatchStatus, BatchSummary
from lexo.gui.batch_dialog import BatchOcrDialog
from lexo.gui.qt import QDialog, QMessageBox, QProgressDialog, Qt
from lexo.gui.worker import BatchOcrWorker
from lexo.pipeline.engine import CancellationToken


class BatchMixin:
    def batch_ocr(self) -> None:
        if self.batch_worker is not None or self.worker is not None or self.edit_worker is not None:
            return
        dialog = BatchOcrDialog(self)
        if dialog.exec() != QDialog.Accepted:
            return
        self._start_batch_ocr(dialog.configuration())

    def _start_batch_ocr(self, config: BatchOcrConfig) -> None:
        self.batch_token = CancellationToken()
        self.batch_worker = BatchOcrWorker(self.service, config, self.batch_token)
        self.batch_progress = QProgressDialog(
            "Starting batch OCR...", "Cancel", 0, config.total, self
        )
        self.batch_progress.setWindowTitle("Batch OCR")
        self.batch_progress.setWindowModality(Qt.WindowModal)
        self.batch_progress.setMinimumDuration(0)
        self.batch_progress.setValue(0)
        self.batch_progress.canceled.connect(self._cancel_batch_ocr)
        self.batch_worker.event.connect(self._on_batch_event)
        self.batch_worker.done.connect(self._batch_done)
        self.batch_worker.failed.connect(self._batch_failed)
        self.batch_worker.auth_required.connect(
            lambda message: self._batch_auth_required(message, config)
        )
        self.batch_worker.cancelled.connect(self._batch_cancelled)
        self.batch_worker.start()
        self._refresh()

    def _on_batch_event(self, event: BatchEvent) -> None:
        if event.status == BatchStatus.STARTED:
            label = f"OCR {event.source.name} ({event.position}/{event.total})"
            self.batch_progress.setLabelText(label)
            self.status.showMessage(label)
            return
        detail = f": {event.message}" if event.message else ""
        label = f"{event.status.title()}: {event.source.name}{detail}"
        self.batch_progress.setLabelText(label)
        self.batch_progress.setValue(event.position)
        self.status.showMessage(label)

    def _batch_done(self, summary: BatchSummary) -> None:
        self._finish_batch_worker()
        message = (
            f"{summary.written} file(s) written\n"
            f"{summary.skipped} skipped\n"
            f"{summary.failed} failed or missing"
        )
        QMessageBox.information(self, "Batch OCR complete", message)
        self.status.showMessage("Batch OCR complete")

    def _batch_failed(self, message: str) -> None:
        self._finish_batch_worker()
        QMessageBox.critical(self, "Batch OCR failed", message)
        self.status.showMessage("Batch OCR failed")

    def _batch_auth_required(self, message: str, config: BatchOcrConfig) -> None:
        self._finish_batch_worker()
        answer = QMessageBox.question(
            self,
            "Sign in required",
            f"{message}\n\nSign in to Google now?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.Yes,
        )
        if answer == QMessageBox.Yes and self.login():
            self._start_batch_ocr(config)

    def _cancel_batch_ocr(self) -> None:
        if self.batch_token is not None:
            self.batch_token.cancel()
            self.batch_progress.setLabelText("Cancelling...")

    def _batch_cancelled(self) -> None:
        self._finish_batch_worker()
        self.status.showMessage("Batch OCR cancelled")

    def _finish_batch_worker(self) -> None:
        worker = self.batch_worker
        self.batch_worker = None
        self.batch_token = None
        if self.batch_progress is not None:
            self.batch_progress.close()
            self.batch_progress.deleteLater()
            self.batch_progress = None
        if worker is not None:
            worker.wait()
            worker.deleteLater()
        self._refresh()
