"""Opening, the page model, rendering, proofread text, saving, and export.

A mixin of `MainWindow`. The document editing itself lives in `WorkingDocument`;
this layer is the bridge between that model and the Qt widgets.
"""

from __future__ import annotations

import base64
from dataclasses import replace
from pathlib import Path

from lexo.domain.models import ExtractedDoc, TextKind
from lexo.domain.ranges import PageRanges
from lexo.export import EXTENSIONS
from lexo.gui.constants import IMAGE_FILTER
from lexo.gui.document import WorkingDocument
from lexo.gui.icons import material_icon
from lexo.gui.qt import (
    QApplication,
    QColor,
    QFileDialog,
    QIcon,
    QListWidgetItem,
    QMessageBox,
    QPainter,
    QPixmap,
    Qt,
)
from lexo.gui.rendering import render_page, render_pdf_page_from_doc

# Per-page status -> (material icon, color) badge drawn on the thumbnail corner.
# Pages that still need OCR get no badge, to keep the strip quiet.
_STATUS_BADGES = {
    "text": ("check_circle", "#6fb0ff"),
    "done": ("check_circle", "#7bd88f"),
    "working": ("schedule", "#f0c674"),
    "failed": ("error", "#ff7b7b"),
}


class DocumentIOMixin:
    # opening

    def open_document(self) -> None:
        if not self._confirm_discard():
            return
        filters = "Documents (*.pdf *.png *.jpg *.jpeg *.tif *.tiff *.bmp);;All files (*.*)"
        filename, _ = QFileDialog.getOpenFileName(self, "Open document", "", filters)
        if filename:
            path = Path(filename)
            self.load_document([path], "pdf" if path.suffix.lower() == ".pdf" else "images")

    def open_image_set(self) -> None:
        if not self._confirm_discard():
            return
        filenames, _ = QFileDialog.getOpenFileNames(self, "Open image set", "", IMAGE_FILTER)
        if filenames:
            self.load_document([Path(p) for p in filenames], "images")

    def close_document(self) -> None:
        if self.document is None or not self._confirm_discard():
            return
        self.document.cleanup()
        self.document = None
        self.doc = None
        self.current = 0
        self.page_count = 0
        self.page_kinds.clear()
        self.page_status.clear()
        self.page_texts.clear()
        self.edits.clear()
        self._thumb_base.clear()
        self.tune.reset_crop()
        self.tune.reset_split()
        self.preview.set_crop_mode(False)
        self.preview.set_split_mode(False)
        self.pages.blockSignals(True)
        self.pages.clear()
        self.pages.blockSignals(False)
        self.preview.clear_image("Open a document to preview pages")
        self.text.blockSignals(True)
        self.text.clear()
        self.text.blockSignals(False)
        self.pages_field.clear()
        self._update_nav()
        self._update_page_count_label()
        self._update_title()
        self.status.showMessage("Closed document")
        self._refresh()

    def load_document(self, paths: list[Path], kind: str) -> None:
        self.status.showMessage("Opening document...")
        self.progress.setRange(0, 0)
        self.progress.show()
        self._pump_ui()
        try:
            document = WorkingDocument.open(self.service.toolkit, self._tmpdir, paths, kind)
        except Exception as exc:
            self.progress.hide()
            QMessageBox.critical(self, "Open failed", str(exc))
            return
        previous = self.document
        self.document = document
        self.current = 0
        self.doc = None
        self.edits.clear()
        self.page_texts.clear()
        try:
            self._load_page_model()
        except Exception as exc:
            self.progress.hide()
            QMessageBox.critical(self, "Open failed", str(exc))
            document.cleanup()
            self.document = previous
            return
        if previous is not None:
            previous.cleanup()
        self.status.showMessage("Rendering page thumbnails...")
        self.progress.setRange(0, max(1, self.page_count))
        self.progress.setValue(0)
        self._pump_ui()
        self._reload_pages()
        self.show_page(0)
        self.progress.hide()
        self.status.showMessage(f"Opened {self._title()} ({self.page_count} page(s))")
        self._update_title()
        self._refresh()
        # If the crop box is toggled on (e.g. the Edit tab is active), show it.
        self._toggle_crop(self.tune.crop_toggle.isChecked())

    # page model

    def _load_page_model(self) -> None:
        assert self.document is not None
        self.page_kinds.clear()
        self.page_status.clear()
        self.page_count = self.document.page_count
        for page in self.document.scan_pages():
            self.page_kinds[page.index] = page.kind
            if page.kind == TextKind.DIGITAL and page.text.strip():
                self.page_texts[page.index] = page.text
                self.page_status[page.index] = "text"
            else:
                self.page_status[page.index] = "needs OCR"

    def _reload_pages(self, select: int | None = 0) -> None:
        self.pages.blockSignals(True)
        self.pages.clear()
        self._thumb_base.clear()
        pdf_doc = None
        try:
            if self.document is not None and self.document.is_pdf:
                import pymupdf

                assert self.document.work_path is not None
                pdf_doc = pymupdf.open(self.document.work_path)
            for index in range(self.page_count):
                item = QListWidgetItem(self._page_item_text(index))
                pixmap = self._thumbnail_pixmap(index, pdf_doc)
                if pixmap is not None:
                    self._thumb_base[index] = pixmap
                    item.setIcon(self._decorate_thumb(pixmap, self.page_status.get(index, "")))
                self.pages.addItem(item)
                if self.progress.isVisible():
                    self.progress.setValue(index + 1)
                    if index % 4 == 0:
                        self._pump_ui()
        finally:
            if pdf_doc is not None:
                pdf_doc.close()
            self.pages.blockSignals(False)
        self._update_nav()
        self._update_page_count_label()
        if select is not None:
            self.pages.setCurrentRow(select if self.page_count else -1)

    def _thumbnail_pixmap(self, index: int, pdf_doc: object | None = None) -> QPixmap | None:
        if self.document is None:
            return None
        path, kind, render_index = self.document.render_target(index)
        try:
            if kind == "pdf" and pdf_doc is not None:
                b64, _, _ = render_pdf_page_from_doc(pdf_doc, render_index, 120, 160)
            else:
                b64, _, _ = render_page(path, kind, 120, 160, render_index)
        except Exception:
            return None
        pixmap = QPixmap()
        if not pixmap.loadFromData(base64.b64decode(b64), "PNG"):
            return None
        return pixmap

    def _decorate_thumb(self, base: QPixmap, status: str) -> QIcon:
        """Draw the per-page status icon in the thumbnail's bottom-right corner."""
        badge = _STATUS_BADGES.get(status)
        if badge is None:
            return QIcon(base)
        name, color = badge
        pm = QPixmap(base)
        d = max(18, pm.width() // 4)
        margin = 3
        x = pm.width() - d - margin
        y = pm.height() - d - margin
        painter = QPainter(pm)
        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(0, 0, 0, 200))
        painter.drawEllipse(x, y, d, d)
        glyph = material_icon(name, color, d - 4).pixmap(d - 4, d - 4)
        painter.drawPixmap(x + 2, y + 2, glyph)
        painter.end()
        return QIcon(pm)

    def _pump_ui(self) -> None:
        app = QApplication.instance()
        if app is not None:
            app.processEvents()

    def show_page(self, index: int) -> None:
        if index < 0 or self.page_count == 0 or self.document is None:
            return
        # Note: do NOT save the editor here. The text shown belongs to the
        # previous page/document, while `current` is about to change - saving now
        # would write stale text into the new page's edits. Edits are captured
        # live by `_capture_edit` on every keystroke, so nothing is lost.
        self.current = min(index, self.page_count - 1)
        path, kind, render_index = self.document.render_target(self.current)
        try:
            b64, _, _ = render_page(path, kind, 1100, 1100, render_index)
        except Exception as exc:
            self.preview.clear_image(f"Could not render page: {exc}")
        else:
            pixmap = QPixmap()
            pixmap.loadFromData(base64.b64decode(b64), "PNG")
            self.preview.set_image(pixmap)
        self.text.blockSignals(True)
        self.text.setPlainText(self.effective_text(self.current))
        self.text.blockSignals(False)
        self.page_input.blockSignals(True)
        self.page_input.setText(str(self.current + 1))
        self.page_input.blockSignals(False)
        self.status.showMessage(f"{self._title()} - page {self.current + 1}/{self.page_count}")
        self._refresh()

    # navigation and pages-strip view

    def go_prev(self) -> None:
        if self.current > 0:
            self.pages.setCurrentRow(self.current - 1)

    def go_next(self) -> None:
        if self.page_count and self.current < self.page_count - 1:
            self.pages.setCurrentRow(self.current + 1)

    def _commit_page_input(self) -> None:
        if self.page_count == 0:
            return
        try:
            value = int(self.page_input.text().strip())
        except ValueError:
            self.page_input.setText(str(self.current + 1))
            return
        value = min(self.page_count, max(1, value))
        if value - 1 != self.current:
            self.pages.setCurrentRow(value - 1)
        else:
            self.page_input.setText(str(value))

    def _update_nav(self) -> None:
        n = self.page_count
        self.page_input.blockSignals(True)
        if n:
            self.page_input.setText(str(self.current + 1))
            self.page_total_label.setText(f"/ {n}")
            self.page_input.setEnabled(True)
        else:
            self.page_input.setText("")
            self.page_total_label.setText("/ 0")
            self.page_input.setEnabled(False)
        self.page_input.blockSignals(False)

    def _on_pages_selection(self) -> None:
        self._update_page_count_label()

    def _update_page_count_label(self) -> None:
        if self.page_count == 0:
            self.page_count_label.setText("No document")
            return
        selected = len({i.row() for i in self.pages.selectedIndexes()})
        plural = "s" if self.page_count != 1 else ""
        base = f"{self.page_count} page{plural}"
        self.page_count_label.setText(f"{base} · {selected} selected" if selected else base)

    def _sync_selection_from_field(self) -> None:
        """Highlight the pages a manually typed range covers, so the user sees them."""
        spec = self.pages_field.text().strip()
        rows: list[int] = []
        if spec:
            try:
                rows = PageRanges.parse(spec).resolve(self.page_count)
            except ValueError:
                return  # incomplete/invalid while typing: leave the selection as is
        self.pages.blockSignals(True)
        self.pages.clearSelection()
        for row in rows:
            item = self.pages.item(row)
            if item is not None:
                item.setSelected(True)
        self.pages.blockSignals(False)
        self._update_page_count_label()

    # proofread text

    def _capture_edit(self) -> None:
        # Fires on every keystroke (textChanged); keeps the current page's edit
        # in sync. Programmatic setPlainText in show_page blocks signals, so this
        # only ever runs for genuine user edits on the page in view.
        self._save_current_text()

    def _save_current_text(self) -> None:
        if self.page_count:
            text = self.text.toPlainText()
            if text != self.page_texts.get(self.current, ""):
                self.edits[self.current] = text
            else:
                self.edits.pop(self.current, None)

    def effective_text(self, index: int) -> str:
        return self.edits.get(index, self.page_texts.get(index, ""))

    def copy_text(self) -> None:
        text = self.text.toPlainText()
        if not text.strip():
            self.notify("No text to copy yet")
            return
        QApplication.clipboard().setText(text)
        self.notify("Copied to clipboard")

    # saving / export

    def save_document(self) -> None:
        if self.document is None:
            return
        if self.document.is_image_set:
            self.save_document_as()
            return
        try:
            self.document.save()
        except Exception as exc:
            QMessageBox.critical(self, "Save failed", str(exc))
            return
        self._update_title()
        self.notify(f"Saved {self.document.source.name}")

    def save_document_as(self) -> None:
        if self.document is None:
            return
        if self.document.is_image_set:
            folder = QFileDialog.getExistingDirectory(self, "Save images to folder")
            if not folder:
                return
            try:
                self.document.save_images(Path(folder))
            except Exception as exc:
                QMessageBox.critical(self, "Save failed", str(exc))
                return
            self._update_title()
            self.notify("Saved images")
            return
        suffix = (self.document.work_path or self.document.work_images[0]).suffix
        out, _ = QFileDialog.getSaveFileName(
            self, "Save As", f"{self._stem()}{suffix}", f"*{suffix}"
        )
        if not out:
            return
        try:
            self.document.save(Path(out))
        except Exception as exc:
            QMessageBox.critical(self, "Save failed", str(exc))
            return
        self._update_title()
        self.notify(f"Saved {Path(out).name}")

    def export_current(self) -> None:
        self._save_current_text()
        doc = self.assembled_doc()
        if doc is None:
            QMessageBox.information(self, "Export", "Run extraction or OCR first.")
            return
        fmt = self.format.currentData()
        try:
            content = self.service.export(doc, fmt)
        except Exception as exc:
            QMessageBox.critical(self, "Export failed", str(exc))
            return
        ext = EXTENSIONS[fmt]
        filename, _ = QFileDialog.getSaveFileName(
            self, "Export text", f"{Path(doc.source_name).stem}{ext}", f"*{ext}"
        )
        if filename:
            Path(filename).write_text(content, encoding="utf-8")
            self.notify(f"Exported {Path(filename).name}")

    def assembled_doc(self) -> ExtractedDoc | None:
        if self.doc is None:
            return None
        return replace(
            self.doc,
            pages=[
                replace(page, text=self.edits.get(page.index, page.text)) for page in self.doc.pages
            ],
        )
