"""The page preview widget: shows a page and doubles as a crop / split surface."""

from __future__ import annotations

from typing import Any

from lexo.domain.models import CropBox
from lexo.gui.qt import QColor, QLabel, QPainter, QPen, QPixmap, QPoint, QRect, Qt, Signal


class PreviewLabel(QLabel):
    """Page preview scaled to fit (letter-boxed, centred).

    Two optional interaction modes, mutually exclusive:
    - crop: a rectangle with four draggable edge lines; drag an edge or corner to
      trim that margin, or drag on empty space to draw a fresh box. `selected_box`
      maps it to a relative `CropBox` and `crop_changed` fires on every edit, so
      the Tune panel's margin fields can stay in sync.
    - split: drag a vertical line; `split_ratio` returns its position in [0, 1].
    """

    crop_changed = Signal()
    page_step = Signal(int)  # wheel over the preview: -1 previous page, +1 next

    _EDGE_GRAB = 10  # px proximity to treat a click as grabbing an edge
    _MIN = 8  # px minimum crop width/height
    _WHEEL_NOTCH = 120  # one wheel detent; touchpads send fractions of this

    def __init__(self) -> None:
        super().__init__()
        self.setAlignment(Qt.AlignCenter)
        self.setMinimumWidth(360)
        self.setMouseTracking(True)
        self.setStyleSheet("background: #202124; color: #f1f3f4;")
        self._source: QPixmap | None = None
        self._shown: QPixmap | None = None
        self._offset = QPoint(0, 0)
        self.crop_mode = False
        self.split_mode = False
        self._origin: QPoint | None = None
        self._selection = QRect()
        self._drag_edges: set[str] = set()
        self._split_ratio = 0.5
        self._dragging_split = False
        self._wheel_accum = 0

    def set_image(self, pixmap: QPixmap) -> None:
        self._source = pixmap
        self._selection = QRect()
        self._origin = None
        self._drag_edges = set()
        self._render()

    def clear_image(self, text: str) -> None:
        self._source = None
        self._shown = None
        self._selection = QRect()
        self.setText(text)

    def _render(self) -> None:
        if self._source is None:
            return
        shown = self._source.scaled(self.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self._shown = shown
        self._offset = QPoint(
            max(0, (self.width() - shown.width()) // 2),
            max(0, (self.height() - shown.height()) // 2),
        )
        self.setPixmap(shown)

    def resizeEvent(self, event: Any) -> None:
        # Keep the crop region (in relative terms) across a resize.
        box = self.selected_box()
        super().resizeEvent(event)
        self._render()
        if box is not None:
            self.set_relative_box(box)
        else:
            self._selection = QRect()

    # modes (mutually exclusive)

    def set_crop_mode(self, on: bool) -> None:
        self.crop_mode = on
        if on:
            self.split_mode = False
        else:
            self._selection = QRect()
        self._origin = None
        self._drag_edges = set()
        self.setCursor(Qt.CrossCursor if on else Qt.ArrowCursor)
        self.setToolTip("Drag the crop edges, or draw a box, then apply crop." if on else "")
        self.update()

    def set_split_mode(self, on: bool) -> None:
        self.split_mode = on
        if on:
            self.crop_mode = False
            self._split_ratio = 0.5
        self._dragging_split = False
        self.setCursor(Qt.SplitHCursor if on else Qt.ArrowCursor)
        self.setToolTip("Drag the split line into place, then apply split." if on else "")
        self.update()

    # results

    def selected_box(self) -> CropBox | None:
        if self._shown is None or self._selection.isNull():
            return None
        rect = self._selection.normalized().translated(-self._offset)
        w, h = self._shown.width(), self._shown.height()
        left = max(0, rect.left())
        top = max(0, rect.top())
        right = min(w, rect.right())
        bottom = min(h, rect.bottom())
        if right - left < self._MIN or bottom - top < self._MIN:
            return None
        return CropBox(left=left / w, top=top / h, right=right / w, bottom=bottom / h)

    def set_relative_box(self, box: CropBox) -> None:
        """Set the visual crop rectangle from a relative CropBox (no signal)."""
        if self._shown is None:
            return
        w, h = self._shown.width(), self._shown.height()
        ox, oy = self._offset.x(), self._offset.y()
        self._selection = QRect(
            QPoint(ox + round(box.left * w), oy + round(box.top * h)),
            QPoint(ox + round(box.right * w), oy + round(box.bottom * h)),
        )
        self.update()

    def split_ratio(self) -> float:
        return self._split_ratio

    # interaction

    def mousePressEvent(self, event: Any) -> None:
        if self._shown is None:
            return
        if self.crop_mode:
            point = event.position().toPoint()
            edges = self._edge_at(point)
            if edges:
                self._drag_edges = edges
                self._origin = None
            else:
                self._origin = self._clamp_to_image(point)
                self._selection = QRect(self._origin, self._origin)
                self._drag_edges = set()
            self.update()
        elif self.split_mode:
            # Only grab the line when the press lands on the page, not the
            # letterbox margins around it.
            if self._image_rect().contains(event.position().toPoint()):
                self._dragging_split = True
                self._set_split_from(event.position().toPoint())

    def mouseMoveEvent(self, event: Any) -> None:
        if self.crop_mode:
            raw = event.position().toPoint()
            if self._drag_edges:
                self._resize_edges(self._clamp_to_image(raw))
                self.crop_changed.emit()
                self.update()
            elif self._origin is not None:
                self._selection = QRect(self._origin, self._clamp_to_image(raw))
                self.crop_changed.emit()
                self.update()
            else:
                self.setCursor(self._cursor_for(raw))
        elif self.split_mode and self._dragging_split:
            # Move only while dragging (not on hover); x is clamped to the page.
            self._set_split_from(event.position().toPoint())

    def mouseReleaseEvent(self, event: Any) -> None:
        if self.crop_mode and (self._drag_edges or self._origin is not None):
            self._selection = self._selection.normalized()
            self._origin = None
            self._drag_edges = set()
            self.crop_changed.emit()
            self.update()
        elif self.split_mode:
            self._dragging_split = False

    def wheelEvent(self, event: Any) -> None:
        # Scroll over the page to flip pages: wheel up = previous, down = next.
        # Accumulate so touchpads (which send sub-notch deltas) step smoothly.
        if self._shown is None:
            event.ignore()
            return
        self._wheel_accum += event.angleDelta().y()
        step = 0
        while self._wheel_accum >= self._WHEEL_NOTCH:
            self._wheel_accum -= self._WHEEL_NOTCH
            step -= 1
        while self._wheel_accum <= -self._WHEEL_NOTCH:
            self._wheel_accum += self._WHEEL_NOTCH
            step += 1
        if step:
            self.page_step.emit(step)
        event.accept()

    # crop geometry helpers

    def _image_rect(self) -> QRect:
        if self._shown is None:
            return QRect()
        return QRect(self._offset, self._shown.size())

    def _clamp_to_image(self, p: QPoint) -> QPoint:
        r = self._image_rect()
        return QPoint(
            min(max(p.x(), r.left()), r.right()),
            min(max(p.y(), r.top()), r.bottom()),
        )

    def _edge_at(self, p: QPoint) -> set[str]:
        if self._selection.isNull():
            return set()
        r = self._selection.normalized()
        g = self._EDGE_GRAB
        edges: set[str] = set()
        within_x = r.left() - g <= p.x() <= r.right() + g
        within_y = r.top() - g <= p.y() <= r.bottom() + g
        if abs(p.x() - r.left()) <= g and within_y:
            edges.add("l")
        if abs(p.x() - r.right()) <= g and within_y:
            edges.add("r")
        if abs(p.y() - r.top()) <= g and within_x:
            edges.add("t")
        if abs(p.y() - r.bottom()) <= g and within_x:
            edges.add("b")
        return edges

    def _resize_edges(self, p: QPoint) -> None:
        r = self._selection.normalized()
        left, top, right, bottom = r.left(), r.top(), r.right(), r.bottom()
        if "l" in self._drag_edges:
            left = min(p.x(), right - self._MIN)
        if "r" in self._drag_edges:
            right = max(p.x(), left + self._MIN)
        if "t" in self._drag_edges:
            top = min(p.y(), bottom - self._MIN)
        if "b" in self._drag_edges:
            bottom = max(p.y(), top + self._MIN)
        self._selection = QRect(QPoint(left, top), QPoint(right, bottom))

    def _cursor_for(self, p: QPoint) -> Any:
        edges = self._edge_at(p)
        if edges in ({"l"}, {"r"}):
            return Qt.SizeHorCursor
        if edges in ({"t"}, {"b"}):
            return Qt.SizeVerCursor
        if edges in ({"l", "t"}, {"r", "b"}):
            return Qt.SizeFDiagCursor
        if edges in ({"r", "t"}, {"l", "b"}):
            return Qt.SizeBDiagCursor
        return Qt.CrossCursor

    def _set_split_from(self, point: QPoint) -> None:
        if self._shown is None:
            return
        x = point.x() - self._offset.x()
        ratio = x / max(1, self._shown.width())
        self._split_ratio = min(0.95, max(0.05, ratio))
        self.update()

    def paintEvent(self, event: Any) -> None:
        super().paintEvent(event)
        if self.crop_mode and not self._selection.isNull():
            r = self._selection.normalized()
            painter = QPainter(self)
            painter.fillRect(r, QColor(30, 136, 229, 58))
            painter.setPen(QPen(QColor(30, 136, 229), 2))
            painter.drawRect(r)
            self._paint_edge_handles(painter, r)
            self._paint_mode_hint(painter, "Crop: drag edges or draw a box")
        elif self.split_mode and self._shown is not None:
            x = self._offset.x() + int(self._split_ratio * self._shown.width())
            top = self._offset.y()
            bottom = top + self._shown.height()
            painter = QPainter(self)
            painter.setPen(QPen(QColor(30, 136, 229), 2))
            painter.drawLine(x, top, x, bottom)
            self._paint_mode_hint(painter, "Split mode: drag the line")

    def _paint_edge_handles(self, painter: QPainter, r: QRect) -> None:
        painter.setPen(QPen(QColor(130, 200, 255), 4))
        mx = (r.left() + r.right()) // 2
        my = (r.top() + r.bottom()) // 2
        for x1, y1, x2, y2 in (
            (r.left(), my - 10, r.left(), my + 10),
            (r.right(), my - 10, r.right(), my + 10),
            (mx - 10, r.top(), mx + 10, r.top()),
            (mx - 10, r.bottom(), mx + 10, r.bottom()),
        ):
            painter.drawLine(x1, y1, x2, y2)

    def _paint_mode_hint(self, painter: QPainter, text: str) -> None:
        rect = QRect(14, 14, 240, 30)
        painter.fillRect(rect, QColor(12, 18, 28, 205))
        painter.setPen(QPen(QColor(255, 255, 255), 1))
        painter.drawText(rect, Qt.AlignCenter, text)
