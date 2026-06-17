"""Central PySide6 import shim for the GUI package.

Importing Qt happens in exactly one place. Every other GUI module imports the
names it needs from here, so a machine without PySide6 can still import
`lexo.gui` (only `run` raises). `QT_AVAILABLE` tells callers which case they are
in.
"""

from __future__ import annotations

try:  # PySide6 is optional until the user syncs GUI dependencies.
    from PySide6.QtCore import (
        QPoint,
        QPropertyAnimation,
        QRect,
        QSettings,
        QSize,
        Qt,
        QThread,
        QTimer,
        Signal,
    )
    from PySide6.QtGui import (
        QAction,
        QColor,
        QFont,
        QFontDatabase,
        QIcon,
        QKeySequence,
        QPainter,
        QPen,
        QPixmap,
    )
    from PySide6.QtWidgets import (
        QApplication,
        QButtonGroup,
        QCheckBox,
        QComboBox,
        QDockWidget,
        QFileDialog,
        QFrame,
        QGraphicsOpacityEffect,
        QGridLayout,
        QGroupBox,
        QHBoxLayout,
        QInputDialog,
        QLabel,
        QLineEdit,
        QListWidget,
        QListWidgetItem,
        QMainWindow,
        QMenu,
        QMessageBox,
        QPlainTextEdit,
        QProgressBar,
        QPushButton,
        QRadioButton,
        QScrollArea,
        QSizePolicy,
        QSpinBox,
        QSplitter,
        QStackedWidget,
        QStatusBar,
        QStyle,
        QStyledItemDelegate,
        QTabWidget,
        QToolBar,
        QToolButton,
        QVBoxLayout,
        QWidget,
    )

    QT_AVAILABLE = True
except ModuleNotFoundError:  # pragma: no cover - depends on optional GUI env
    QT_AVAILABLE = False

    class _MissingQt:
        def __getattr__(self, _name: str) -> int:
            return 0

    class _MissingSignal:
        def __init__(self, *_: object) -> None:
            pass

        def connect(self, *_: object) -> None:
            pass

        def emit(self, *_: object) -> None:
            pass

    class _MissingWidget:
        def __init__(self, *_: object, **__: object) -> None:
            pass

    Qt = _MissingQt()  # type: ignore[assignment]
    Signal = _MissingSignal  # type: ignore[assignment]
    QPoint = QRect = QSettings = QSize = QThread = _MissingWidget  # type: ignore[assignment]
    QPropertyAnimation = QTimer = _MissingWidget  # type: ignore[assignment]
    QGraphicsOpacityEffect = _MissingWidget  # type: ignore[assignment]
    QAction = QColor = QIcon = QKeySequence = _MissingWidget  # type: ignore[assignment]
    QFont = QFontDatabase = _MissingWidget  # type: ignore[assignment]
    QPainter = QPen = QPixmap = _MissingWidget  # type: ignore[assignment]
    QApplication = QButtonGroup = QCheckBox = QComboBox = QDockWidget = _MissingWidget  # type: ignore[assignment]
    QFileDialog = QFrame = QGridLayout = QGroupBox = QHBoxLayout = _MissingWidget  # type: ignore[assignment]
    QInputDialog = _MissingWidget  # type: ignore[assignment]
    QLabel = QLineEdit = QListWidget = QListWidgetItem = _MissingWidget  # type: ignore[assignment]
    QMainWindow = QMenu = QMessageBox = QPlainTextEdit = _MissingWidget  # type: ignore[assignment]
    QProgressBar = QPushButton = QRadioButton = QSpinBox = _MissingWidget  # type: ignore[assignment]
    QScrollArea = _MissingWidget  # type: ignore[assignment]
    QSizePolicy = _MissingWidget  # type: ignore[assignment]
    QSplitter = QStackedWidget = QStatusBar = QStyle = _MissingWidget  # type: ignore[assignment]
    QStyledItemDelegate = _MissingWidget  # type: ignore[assignment]
    QTabWidget = QToolBar = QToolButton = _MissingWidget  # type: ignore[assignment]
    QVBoxLayout = QWidget = _MissingWidget  # type: ignore[assignment]


__all__ = [
    "QT_AVAILABLE",
    "QAction",
    "QApplication",
    "QButtonGroup",
    "QCheckBox",
    "QColor",
    "QComboBox",
    "QDockWidget",
    "QFileDialog",
    "QFont",
    "QFontDatabase",
    "QFrame",
    "QGraphicsOpacityEffect",
    "QGridLayout",
    "QGroupBox",
    "QHBoxLayout",
    "QIcon",
    "QInputDialog",
    "QKeySequence",
    "QLabel",
    "QLineEdit",
    "QListWidget",
    "QListWidgetItem",
    "QMainWindow",
    "QMenu",
    "QMessageBox",
    "QPainter",
    "QPen",
    "QPixmap",
    "QPlainTextEdit",
    "QPoint",
    "QProgressBar",
    "QPropertyAnimation",
    "QPushButton",
    "QRadioButton",
    "QRect",
    "QScrollArea",
    "QSettings",
    "QSize",
    "QSizePolicy",
    "QSpinBox",
    "QSplitter",
    "QStackedWidget",
    "QStatusBar",
    "QStyle",
    "QStyledItemDelegate",
    "QTabWidget",
    "Qt",
    "QThread",
    "QTimer",
    "QToolBar",
    "QToolButton",
    "QVBoxLayout",
    "QWidget",
    "Signal",
]
