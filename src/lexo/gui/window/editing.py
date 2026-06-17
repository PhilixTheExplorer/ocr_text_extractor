"""Document-editing actions: scope resolution, edits, and the pages context menu.

A mixin of `MainWindow`. Each handler resolves the target pages, calls the
matching `WorkingDocument` operation, and refreshes the view.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import replace
from pathlib import Path

from lexo.domain.models import CropBox
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

    def _run_edit(self, edit: Callable[[], bool]) -> None:
        if self.document is None:
            return
        try:
            structural = edit()
        except Exception as exc:
            QMessageBox.critical(self, "Edit failed", str(exc))
            return
        self._after_edit(structural)

    def _after_edit(self, structural: bool) -> None:
        if structural:
            # Page count or order changed: any prior OCR/extract result is stale.
            self.doc = None
            self.page_texts.clear()
            self.edits.clear()
            self._load_page_model()
        keep = min(self.current, self.page_count - 1)
        self._reload_pages(select=None)
        self.pages.setCurrentRow(keep)
        self.show_page(keep)
        self._update_title()
        self._refresh()

    # operations

    def rotate_scope(self, degrees: int) -> None:
        rows = self._scope_rows()
        self._run_edit(lambda: self.document.rotate(rows, degrees))

    def rotate_selected(self, degrees: int) -> None:
        rows = self._selected_rows()
        self._run_edit(lambda: self.document.rotate(rows, degrees))

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
        try:
            structural = self.document.crop(rows, self._crop_box_from_margins())
        except Exception as exc:
            QMessageBox.critical(self, "Crop failed", str(exc))
            return
        self.tune.reset_crop()
        self._after_edit(structural)

    def remove_selected(self) -> None:
        rows = self._selected_rows()
        self._run_edit(lambda: self.document.remove(rows))

    def move_selected(self, offset: int) -> None:
        """Move the selected pages one slot up (offset -1) or down (+1)."""
        if self.document is None or self.page_count < 2:
            return
        sel = set(self._selected_rows())
        order = reorder_for_move(self.page_count, sel, offset)
        if order is None:
            return
        try:
            self.document.reorder(order)
        except Exception as exc:
            QMessageBox.critical(self, "Move failed", str(exc))
            return
        new_selected = [pos for pos, val in enumerate(order) if val in sel]
        new_current = order.index(self.current)
        # Carry proofread text, edits, and status with each page to its new slot,
        # so reordering does not throw away work. order[pos] is the old index now
        # sitting at position pos.
        self._remap_page_state(order)
        self._reload_pages(select=None)
        self.pages.blockSignals(True)
        self.pages.clearSelection()
        for pos in new_selected:
            item = self.pages.item(pos)
            if item is not None:
                item.setSelected(True)
        self.pages.blockSignals(False)
        self.pages.setCurrentRow(new_current)
        self.show_page(new_current)
        self._update_title()
        self._refresh()

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
        self._run_edit(lambda: self.document.split_spreads(ratio))

    def append_pdfs(self) -> None:
        if self.document is None or not self.document.is_pdf:
            QMessageBox.information(self, "PDF required", "Open a PDF to use this.")
            return
        filenames, _ = QFileDialog.getOpenFileNames(self, "Append PDF(s)", "", "PDF (*.pdf)")
        if not filenames:
            return
        extra = [Path(p) for p in filenames]
        self._run_edit(lambda: self.document.append(extra))

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
