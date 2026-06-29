"""Document-editing actions: scope resolution, edits, and the pages context menu.

A mixin of `MainWindow`. Each handler resolves the target pages, calls the
matching `WorkingDocument` operation, and refreshes the view.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import replace
from pathlib import Path

from lexo.domain.models import CropBox
from lexo.gui.edit_worker import EditResult, EditWorker
from lexo.gui.qt import QFileDialog, QInputDialog, QMenu, QMessageBox, QPoint
from lexo.gui.tune_panel import SCOPE_ALL, SCOPE_SELECTED


def reorder_for_move(n: int, selected: set[int], offset: int) -> list[int] | None:
    """New page order after nudging the selected pages one slot up/down.

    `selected` holds page positions; `offset` is -1 (up) or +1 (down). Returns a
    permutation of range(n), or None if the move is a no-op (already at the edge).
    The selected block keeps its relative order and moves as a unit.
    """
    if not selected:
        return None
    if offset < 0 and 0 in selected:
        return None
    if offset > 0 and (n - 1) in selected:
        return None
    order = list(range(n))
    if offset < 0:
        for i in range(1, n):
            if order[i] in selected and order[i - 1] not in selected:
                order[i - 1], order[i] = order[i], order[i - 1]
    else:
        for i in range(n - 2, -1, -1):
            if order[i] in selected and order[i + 1] not in selected:
                order[i], order[i + 1] = order[i + 1], order[i]
    return None if order == list(range(n)) else order


class EditingMixin:
    # scope / selection

    def _selected_rows(self) -> list[int]:
        rows = sorted({i.row() for i in self.pages.selectedIndexes()})
        return rows or ([self.current] if self.page_count else [])

    def _scope_rows(self) -> list[int] | None:
        scope = self.tune.scope()
        if scope == SCOPE_ALL:
            return None
        if scope == SCOPE_SELECTED:
            return self._selected_rows()
        return [self.current]

    # apply

    def _run_edit(self, edit: Callable[[], bool], *, message: str = "Applying edit…") -> None:
        """Run a page edit off the UI thread: mutate the file, re-scan, and
        re-render thumbnails in a worker, then rebuild the view on completion.
        The page strip is locked meanwhile so the UI never touches PyMuPDF
        concurrently with the worker."""
        if self.document is None or self.worker is not None or self.edit_worker is not None:
            return
        # Set edit_worker before _begin_edit so the _refresh inside it sees the
        # busy state and disables Run/OCR/edit controls.
        self.edit_worker = EditWorker(self.document, edit)
        self.edit_worker.finished_ok.connect(self._finalize_edit)
        self.edit_worker.failed.connect(self._fail_edit)
        self._begin_edit(message)
        self.edit_worker.start()

    def _begin_edit(self, message: str) -> None:
        self._set_busy(message)
        # No page may be rendered on the UI thread while the worker uses PyMuPDF.
        self.pages.setEnabled(False)
        self._refresh()

    def _finalize_edit(self, result: EditResult) -> None:
        if result.structural:
            # Page count or order changed: any prior OCR/extract result is stale.
            self.doc = None
            self.page_texts.clear()
            self.edits.clear()
            self.page_count = result.page_count
            assert result.scan is not None
            self._apply_scan_to_model(result.scan)
        keep = min(self.current, self.page_count - 1)
        self.progress.setRange(0, max(1, self.page_count))
        self.progress.setValue(0)
        self._reload_pages(select=None, thumbs=result.thumbs)
        self.pages.blockSignals(True)
        self.pages.setCurrentRow(keep)
        self.pages.blockSignals(False)
        self.show_page(keep)
        self._update_title()
        self._end_edit()

    def _fail_edit(self, message: str) -> None:
        self._end_edit()
        QMessageBox.critical(self, "Edit failed", message)

    def _end_edit(self) -> None:
        worker = self.edit_worker
        self.edit_worker = None
        # Runs from the worker's own signal, so run() has returned; wait for the
        # QThread to finish before releasing it (see ProcessWorker teardown).
        if worker is not None:
            worker.wait()
            worker.deleteLater()
        self.pages.setEnabled(True)
        self.progress.hide()
        self._refresh()

    # operations

    def rotate_scope(self, degrees: int) -> None:
        rows = self._scope_rows()
        self._run_edit(lambda: self.document.rotate(rows, degrees), message="Rotating pages…")

    def rotate_selected(self, degrees: int) -> None:
        rows = self._selected_rows()
        self._run_edit(lambda: self.document.rotate(rows, degrees), message="Rotating pages…")

    def _toggle_crop(self, on: bool) -> None:
        # Only crop when a document is open; the Edit tab can be active with none.
        on = on and self.document is not None
        if on:
            self.tune.reset_split()
        self.preview.set_crop_mode(on)
        if on:
            # Start with a visible inset box so there is something to drag right away.
            if self.tune.crop_margins() == (0, 0, 0, 0):
                self.tune.set_crop_margins(10, 10, 10, 10)
            self._sync_crop_to_preview()
            self.status.showMessage("Drag the crop edges or draw a box, then 'Apply crop'.")

    def _crop_box_from_margins(self) -> CropBox:
        top, bottom, left, right = self.tune.crop_margins()
        return CropBox(
            left=left / 100, top=top / 100, right=1 - right / 100, bottom=1 - bottom / 100
        )

    def _sync_crop_to_preview(self) -> None:
        """Margin fields -> the preview's crop rectangle."""
        if self.preview.crop_mode:
            self.preview.set_relative_box(self._crop_box_from_margins())

    def _sync_crop_from_preview(self) -> None:
        """The preview's crop rectangle -> margin fields."""
        box = self.preview.selected_box()
        if box is None:
            return
        self.tune.set_crop_margins(
            top=box.top * 100,
            bottom=(1 - box.bottom) * 100,
            left=box.left * 100,
            right=(1 - box.right) * 100,
        )

    def apply_crop(self) -> None:
        if self.document is None:
            return
        top, bottom, left, right = self.tune.crop_margins()
        if left + right >= 100 or top + bottom >= 100:
            QMessageBox.information(self, "Crop", "Those margins remove the entire page.")
            return
        if top == bottom == left == right == 0:
            QMessageBox.information(self, "Crop", "Set crop margins or draw a crop box first.")
            return
        rows = self._scope_rows()
        # Capture the box before resetting the crop UI; the edit runs later, on the
        # worker thread.
        box = self._crop_box_from_margins()
        self.tune.reset_crop()
        self._run_edit(lambda: self.document.crop(rows, box), message="Cropping pages…")

    def remove_selected(self) -> None:
        rows = self._selected_rows()
        plural = "s" if len(rows) != 1 else ""
        self._run_edit(
            lambda: self.document.remove(rows), message=f"Removing {len(rows)} page{plural}…"
        )

    def move_selected(self, offset: int) -> None:
        """Move the selected pages one slot up (offset -1) or down (+1)."""
        if self.document is None or self.page_count < 2:
            return
        if self.worker is not None or self.edit_worker is not None:
            return
        sel = set(self._selected_rows())
        order = reorder_for_move(self.page_count, sel, offset)
        if order is None:
            return
        # Reorder keeps the page model, which the GUI remaps onto the new order, so
        # the worker skips the rescan. Stash what the finalize step needs.
        self._pending_move = (order, sel)
        self.edit_worker = EditWorker(
            self.document, lambda: self.document.reorder(order), scan=False
        )
        self.edit_worker.finished_ok.connect(self._finalize_move)
        self.edit_worker.failed.connect(self._fail_edit)
        self._begin_edit("Reordering pages…")
        self.edit_worker.start()

    def _finalize_move(self, result: EditResult) -> None:
        order, sel = self._pending_move
        self.page_count = result.page_count
        # Carry proofread text, edits, and status with each page to its new slot,
        # so reordering does not throw away work. order[pos] is the old index now
        # sitting at position pos.
        self._remap_page_state(order)
        self.progress.setRange(0, max(1, self.page_count))
        self.progress.setValue(0)
        self._reload_pages(select=None, thumbs=result.thumbs)
        new_selected = [pos for pos, val in enumerate(order) if val in sel]
        new_current = order.index(self.current)
        self.pages.blockSignals(True)
        self.pages.clearSelection()
        for pos in new_selected:
            item = self.pages.item(pos)
            if item is not None:
                item.setSelected(True)
        self.pages.setCurrentRow(new_current)
        self.pages.blockSignals(False)
        self.show_page(new_current)
        self._update_title()
        self._end_edit()
        self.progress.hide()

    def _remap_page_state(self, order: list[int]) -> None:
        """Move per-page state so it follows pages through a reorder.

        `order[pos]` is the old index now at position `pos`. Dicts keyed by page
        position are rebuilt; the assembled `doc` (keyed by `page.index`) has its
        indices rewritten through the inverse permutation.
        """

        def follow(d: dict[int, object]) -> dict[int, object]:
            return {pos: d[order[pos]] for pos in range(len(order)) if order[pos] in d}

        self.page_texts = follow(self.page_texts)  # type: ignore[assignment]
        self.edits = follow(self.edits)  # type: ignore[assignment]
        self.page_status = follow(self.page_status)  # type: ignore[assignment]
        self.page_kinds = follow(self.page_kinds)  # type: ignore[assignment]
        if self.doc is not None:
            inverse = [0] * len(order)
            for pos, old in enumerate(order):
                inverse[old] = pos
            pages = sorted(
                (replace(page, index=inverse[page.index]) for page in self.doc.pages),
                key=lambda page: page.index,
            )
            self.doc = replace(self.doc, pages=pages)

    def extract_selected(self) -> None:
        if self.document is None:
            return
        rows = self._selected_rows()
        if not rows:
            return
        if self.document.is_pdf:
            out, _ = QFileDialog.getSaveFileName(
                self, "Extract pages to", f"{self._stem()}_pages.pdf", "PDF (*.pdf)"
            )
            target = Path(out) if out else None
        else:
            folder = QFileDialog.getExistingDirectory(self, "Extract images to folder")
            target = Path(folder) if folder else None
        if target is None:
            return
        try:
            self.document.extract(rows, target)
        except Exception as exc:
            QMessageBox.critical(self, "Extract failed", str(exc))
            return
        self.notify(f"Extracted {len(rows)} page(s)")

    def split_pdf(self) -> None:
        if self.document is None or not self.document.is_pdf:
            QMessageBox.information(self, "PDF required", "Open a PDF to use this.")
            return
        every, ok = QInputDialog.getInt(self, "Split PDF", "Pages per output file", 1, 1)
        if not ok:
            return
        out_dir = QFileDialog.getExistingDirectory(self, "Output folder")
        try:
            results = self.document.split(every, Path(out_dir) if out_dir else None)
        except Exception as exc:
            QMessageBox.critical(self, "Split failed", str(exc))
            return
        self.notify(f"Split into {len(results)} file(s)")

    def _toggle_split(self, on: bool) -> None:
        if on:
            if self.document is None or not self.document.is_pdf:
                self.tune.reset_split()
                QMessageBox.information(self, "PDF required", "Open a PDF to split spreads.")
                return
            self.tune.reset_crop()
            self.preview.set_split_mode(True)
            self.status.showMessage("Drag the line, then 'Split two-up at line'.")
        else:
            self.preview.set_split_mode(False)

    def apply_split(self) -> None:
        if self.document is None or not self.document.is_pdf:
            QMessageBox.information(self, "PDF required", "Open a PDF to use this.")
            return
        ratio = self.preview.split_ratio()
        self.tune.reset_split()
        self._run_edit(lambda: self.document.split_spreads(ratio), message="Splitting spreads…")

    def append_pdfs(self) -> None:
        if self.document is None or not self.document.is_pdf:
            QMessageBox.information(self, "PDF required", "Open a PDF to use this.")
            return
        filenames, _ = QFileDialog.getOpenFileNames(self, "Append PDF(s)", "", "PDF (*.pdf)")
        if not filenames:
            return
        extra = [Path(p) for p in filenames]
        self._run_edit(lambda: self.document.append(extra), message="Appending pages…")

    # pages-strip context menu

    def _pages_context_menu(self, point: QPoint) -> None:
        if self.page_count == 0:
            return
        menu = QMenu(self)
        menu.addAction(self.move_up_act)
        menu.addAction(self.move_down_act)
        menu.addSeparator()
        menu.addAction(self.rotate_left_act)
        menu.addAction(self.rotate_right_act)
        menu.addSeparator()
        menu.addAction(self.extract_pages_act)
        menu.addAction(self.remove_pages_act)
        menu.exec(self.pages.mapToGlobal(point))
