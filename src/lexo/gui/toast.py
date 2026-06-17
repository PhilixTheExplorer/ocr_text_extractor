"""A small auto-dismissing toast overlay for transient confirmations.

The status bar is easy to miss, so success messages (copied, saved, exported)
also surface here: a floating pill near the bottom of the window that fades out
on its own. It is click-through, so it never blocks the UI underneath.
"""

from __future__ import annotations

from lexo.gui.qt import (
    QGraphicsOpacityEffect,
    QLabel,
    QPropertyAnimation,
    Qt,
    QTimer,
    QWidget,
)


class Toast(QLabel):
    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent)
        self.setObjectName("Toast")
        self.setAlignment(Qt.AlignCenter)
        self.setVisible(False)
        self.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self._opacity = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self._opacity)
        self._fade = QPropertyAnimation(self._opacity, b"opacity", self)
        self._fade.setDuration(350)
        self._fade.finished.connect(self._on_fade_done)
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self._start_fade)

    def show_message(self, text: str, msec: int = 1600) -> None:
        self._timer.stop()
        self._fade.stop()
        self.setText(text)
        self.adjustSize()
        self._reposition()
        self._opacity.setOpacity(1.0)
        self.setVisible(True)
        self.raise_()
        self._timer.start(msec)

    def _start_fade(self) -> None:
        self._fade.stop()
        self._fade.setStartValue(1.0)
        self._fade.setEndValue(0.0)
        self._fade.start()

    def _on_fade_done(self) -> None:
        if self._opacity.opacity() <= 0.01:
            self.setVisible(False)

    def _reposition(self) -> None:
        parent = self.parentWidget()
        if parent is None:
            return
        x = (parent.width() - self.width()) // 2
        y = parent.height() - self.height() - 56
        self.move(max(12, x), max(12, y))
