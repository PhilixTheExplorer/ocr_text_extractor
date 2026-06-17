"""PySide6 desktop entry point.

Thin launcher: it creates the application, installs the SIGINT handler, and shows
the `MainWindow` (whose behaviour is composed from the `lexo.gui.window` mixins).
The desktop flow is open -> tune -> run (extract text layer or OCR) -> proofread
-> export, all driving the same `LexoService` as the CLI.
"""

from __future__ import annotations

import signal
import sys

from lexo.gui.qt import QT_AVAILABLE, QApplication
from lexo.gui.resources import app_icon
from lexo.gui.style import load_style
from lexo.gui.window import MainWindow

__all__ = ["MainWindow", "run"]


def run() -> None:
    if not QT_AVAILABLE:
        raise RuntimeError("PySide6 is not installed. Run `uv sync` after updating dependencies.")
    # Let Ctrl+C in the launching terminal terminate the app immediately. Qt's
    # C++ event loop never runs Python's SIGINT handler, so without this a
    # pending Ctrl+C is deferred and surfaces as a KeyboardInterrupt inside the
    # next Python override to run (e.g. closeEvent). SIG_DFL avoids that.
    signal.signal(signal.SIGINT, signal.SIG_DFL)
    app = QApplication.instance() or QApplication(sys.argv)
    app.setApplicationName("Lexo")
    app.setWindowIcon(app_icon())
    app.setStyleSheet(load_style())
    win = MainWindow()
    win.show()
    app.exec()


if __name__ == "__main__":
    run()
