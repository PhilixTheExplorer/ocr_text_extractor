"""The start screen shown when no document is open.

A self-contained widget: the logo, a short intro, the two import buttons, and a
how-it-works guide. It only needs the open actions (for their icons and to
trigger them), so it carries no window state of its own.
"""

from __future__ import annotations

from lexo.gui.qt import (
    QAction,
    QLabel,
    QPushButton,
    QScrollArea,
    QSize,
    QSizePolicy,
    Qt,
    QVBoxLayout,
    QWidget,
)
from lexo.gui.resources import logo_pixmap

COLUMN_WIDTH = 560


class WelcomePanel(QWidget):
    def __init__(
        self,
        open_action: QAction,
        open_set_action: QAction,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("ImportPanel")

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setObjectName("ImportScroll")
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        outer.addWidget(scroll)

        content = QWidget()
        content.setObjectName("ImportContent")
        scroll.setWidget(content)

        layout = QVBoxLayout(content)
        layout.setContentsMargins(32, 36, 32, 32)
        layout.setSpacing(0)
        layout.addStretch(1)

        # Above the buttons: who/what the app is.
        welcome_group = QWidget()
        welcome_group.setFixedWidth(COLUMN_WIDTH)
        welcome_layout = QVBoxLayout(welcome_group)
        welcome_layout.setContentsMargins(0, 0, 0, 0)
        welcome_layout.setSpacing(8)

        logo = QLabel()
        logo.setAlignment(Qt.AlignCenter)
        pixmap = logo_pixmap()
        if not pixmap.isNull():
            logo.setPixmap(pixmap.scaled(72, 72, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        title = QLabel("Welcome to Lexo")
        title.setObjectName("WelcomeTitle")
        title.setAlignment(Qt.AlignCenter)
        acronym = QLabel(
            "<span style='color:#9aa7b4;'><b>L</b>ocal <b>EX</b>traction and <b>O</b>CR</span>"
        )
        acronym.setObjectName("WelcomeAcronym")
        acronym.setTextFormat(Qt.RichText)
        acronym.setAlignment(Qt.AlignCenter)
        about = QLabel(
            "Burmese-first, with free high-accuracy OCR through your own Google account."
        )
        about.setObjectName("WelcomeBody")
        about.setAlignment(Qt.AlignCenter)
        about.setWordWrap(True)
        about.setFixedWidth(COLUMN_WIDTH)
        about.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Minimum)
        for widget in (logo, title, acronym, about):
            welcome_layout.addWidget(widget, 0, Qt.AlignCenter)
        layout.addWidget(welcome_group, 0, Qt.AlignCenter)
        layout.addSpacing(28)

        actions_group = QWidget()
        actions_layout = QVBoxLayout(actions_group)
        actions_layout.setContentsMargins(0, 0, 0, 0)
        actions_layout.setSpacing(10)

        import_button = QPushButton("Import PDF or Image")
        import_button.setObjectName("PrimaryButton")
        import_button.setIcon(open_action.icon())
        import_button.setIconSize(QSize(18, 18))
        import_button.setToolTip("Open a single PDF or image")
        import_button.clicked.connect(open_action.trigger)
        image_set_button = QPushButton("Select Image Set")
        image_set_button.setObjectName("SecondaryButton")
        image_set_button.setIcon(open_set_action.icon())
        image_set_button.setIconSize(QSize(18, 18))
        image_set_button.setToolTip("Open several images as one multi-page document")
        image_set_button.clicked.connect(open_set_action.trigger)
        actions_layout.addWidget(import_button, 0, Qt.AlignCenter)
        actions_layout.addWidget(image_set_button, 0, Qt.AlignCenter)
        layout.addWidget(actions_group, 0, Qt.AlignCenter)

        # Below the buttons: how the workflow runs.
        layout.addSpacing(30)
        steps = QLabel(
            "<div align='left'><b>How it works</b></div>"
            "<table cellspacing='0' cellpadding='3'>"
            "<tr><td valign='top'>1.</td><td>Open a PDF, image, or image set</td></tr>"
            "<tr><td valign='top'>2.</td><td>Tune pages: rotate, crop, split, or reorder</td></tr>"
            "<tr><td valign='top'>3.</td>"
            "<td>Extract the text layer, or run Google Docs OCR on scans</td></tr>"
            "<tr><td valign='top'>4.</td>"
            "<td>Proofread, then export to text, Markdown, or JSONL</td></tr>"
            "</table>"
        )
        steps.setObjectName("WelcomeSteps")
        steps.setTextFormat(Qt.RichText)
        steps.setAlignment(Qt.AlignCenter)
        steps.setWordWrap(True)
        steps.setFixedWidth(COLUMN_WIDTH)
        setup = QLabel(
            "Google Docs OCR is free but needs a one-time setup: place a "
            "<b>credentials.json</b> from Google Cloud in your config folder, then "
            "sign in under the Account menu. See the README for the full steps. "
            "Text-layer extraction needs no setup and no account."
        )
        setup.setObjectName("WelcomeSetup")
        setup.setTextFormat(Qt.RichText)
        setup.setAlignment(Qt.AlignLeft)
        setup.setWordWrap(True)
        setup.setFixedWidth(COLUMN_WIDTH)
        layout.addWidget(steps, 0, Qt.AlignCenter)
        layout.addSpacing(12)
        layout.addWidget(setup, 0, Qt.AlignCenter)
        layout.addStretch(1)
