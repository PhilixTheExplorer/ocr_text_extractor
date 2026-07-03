"""Window construction: actions, menus, body, docks, status bar.

A mixin of `MainWindow`; the build methods set attributes and wire signals onto
`self`, whose handlers live in the other window mixins.
"""

from __future__ import annotations

from lexo.export import EXTENSIONS
from lexo.gui.icons import material_icon
from lexo.gui.preview import PreviewLabel, PreviewScrollArea
from lexo.gui.qt import (
    QAction,
    QButtonGroup,
    QComboBox,
    QDockWidget,
    QGroupBox,
    QHBoxLayout,
    QKeySequence,
    QLabel,
    QLineEdit,
    QListWidget,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QSize,
    QSizePolicy,
    QSplitter,
    QStackedWidget,
    QStatusBar,
    QStyle,
    QStyledItemDelegate,
    Qt,
    QToolButton,
    QVBoxLayout,
    QWidget,
)
from lexo.gui.resources import myanmar_font_family
from lexo.gui.tune_panel import TunePanel
from lexo.gui.window.welcome import WelcomePanel


class _NoFocusDelegate(QStyledItemDelegate):
    """Paint list items without the dotted focus rectangle around thumbnails."""

    def paint(self, painter: object, option: object, index: object) -> None:
        option.state &= ~QStyle.State_HasFocus  # type: ignore[attr-defined]
        super().paint(painter, option, index)  # type: ignore[arg-type]


class BuildMixin:
    # Shared height for the preview and text pane headers, so they line up.
    PANE_HEADER_HEIGHT = 44

    def _add_view_toggle_action(self, action: QAction, label: str) -> None:
        # A checkbox icon makes the panel's open/closed state obvious in the menu.
        def sync(checked: bool) -> None:
            action.setText(label)
            icon = "check_box" if checked else "check_box_outline_blank"
            action.setIcon(material_icon(icon, "#7bd88f" if checked else "#7c8794"))

        action.toggled.connect(sync)
        sync(action.isChecked())
        self.view_menu.addAction(action)

    def _make_run_panel_button(self, action: QAction) -> QPushButton:
        button = QPushButton(self)
        button.setObjectName("RunPanelButton")
        button.setIconSize(QSize(18, 18))
        button.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        def sync() -> None:
            button.setText(action.text())
            button.setIcon(action.icon())
            button.setToolTip(action.toolTip())
            button.setEnabled(action.isEnabled())
            button.setVisible(action.isVisible())

        action.changed.connect(sync)
        button.clicked.connect(action.trigger)
        sync()
        return button

    def _set_zoom_label(self, text: str) -> None:
        self.zoom_label.setText(text)

    def _build_actions(self) -> None:
        self.open_act = QAction("Open PDF or Image...", self)
        self.open_act.setIcon(material_icon("folder_open"))
        self.open_act.setShortcut(QKeySequence.Open)
        self.open_act.setToolTip("Open a single PDF or image")
        self.open_act.triggered.connect(self.open_document)
        self.open_set_act = QAction("Open Image Set...", self)
        self.open_set_act.setIcon(material_icon("photo_library"))
        self.open_set_act.setShortcut("Ctrl+Shift+O")
        self.open_set_act.setToolTip("Open several images as one multi-page document")
        self.open_set_act.triggered.connect(self.open_image_set)
        self.save_act = QAction("Save", self)
        self.save_act.setIcon(material_icon("save"))
        self.save_act.setShortcut(QKeySequence.Save)
        self.save_act.setToolTip("Save page edits back to the original file")
        self.save_act.triggered.connect(self.save_document)
        self.save_as_act = QAction("Save As...", self)
        self.save_as_act.setIcon(material_icon("save_alt"))
        self.save_as_act.setShortcut("Ctrl+Shift+S")
        self.save_as_act.setToolTip("Save the edited document to a new file")
        self.save_as_act.triggered.connect(self.save_document_as)
        self.export_act = QAction("Export Text...", self)
        self.export_act.setIcon(material_icon("file_download"))
        self.export_act.setShortcut("Ctrl+E")
        self.export_act.setToolTip("Export the recognized text (text, Markdown, or JSONL)")
        self.export_act.triggered.connect(self.export_current)
        self.close_act = QAction("Close Document", self)
        self.close_act.setShortcut("Ctrl+W")
        self.close_act.setToolTip("Close the current document and return to the start screen")
        self.close_act.triggered.connect(self.close_document)
        self.copy_text_act = QAction("Copy", self)
        self.copy_text_act.setIcon(material_icon("content_copy"))
        self.copy_text_act.setToolTip("Copy this page's text to the clipboard")
        self.copy_text_act.setShortcut("Ctrl+Shift+C")
        self.copy_text_act.setShortcutContext(Qt.ApplicationShortcut)
        self.copy_text_act.triggered.connect(self.copy_text)
        self.exit_act = QAction("Exit", self)
        self.exit_act.setIcon(material_icon("close"))
        self.exit_act.setToolTip("Quit Lexo")
        self.exit_act.triggered.connect(self.close)

        self.run_act = QAction("Run", self)
        self.run_act.setIcon(material_icon("play_arrow"))
        self.run_act.setShortcut("Ctrl+R")
        self.run_act.setToolTip("Extract the text layer, or run OCR on scanned pages")
        self.run_act.triggered.connect(self.run_process)
        self.cancel_act = QAction("Cancel", self)
        self.cancel_act.setIcon(material_icon("cancel"))
        self.cancel_act.setShortcut("Esc")
        self.cancel_act.setToolTip("Stop the current run")
        self.cancel_act.triggered.connect(self.cancel_process)
        self.retry_failed_act = QAction("Retry Failed Pages", self)
        self.retry_failed_act.setIcon(material_icon("replay"))
        self.retry_failed_act.setShortcut("Ctrl+Shift+R")
        self.retry_failed_act.setToolTip("Re-run OCR on the pages that failed in the last run")
        self.retry_failed_act.triggered.connect(self.retry_failed_pages)

        # Selection-based page operations: shared by the Page menu and the
        # pages-strip context menu. Move shortcuts fire app-wide; they do not
        # collide with the text editor's own bindings.
        self.move_up_act = QAction("Move Up", self)
        self.move_up_act.setIcon(material_icon("arrow_upward"))
        self.move_up_act.setShortcut("Ctrl+Shift+Up")
        self.move_up_act.setShortcutContext(Qt.ApplicationShortcut)
        self.move_up_act.setToolTip("Move the selected page(s) one slot earlier")
        self.move_up_act.triggered.connect(lambda *_: self.move_selected(-1))
        self.move_down_act = QAction("Move Down", self)
        self.move_down_act.setIcon(material_icon("arrow_downward"))
        self.move_down_act.setShortcut("Ctrl+Shift+Down")
        self.move_down_act.setShortcutContext(Qt.ApplicationShortcut)
        self.move_down_act.setToolTip("Move the selected page(s) one slot later")
        self.move_down_act.triggered.connect(lambda *_: self.move_selected(1))
        self.rotate_left_act = QAction("Rotate Left 90°", self)
        self.rotate_left_act.setIcon(material_icon("rotate_left"))
        self.rotate_left_act.setToolTip("Rotate the selected page(s) 90° counter-clockwise")
        self.rotate_left_act.triggered.connect(lambda *_: self.rotate_selected(-90))
        self.rotate_right_act = QAction("Rotate Right 90°", self)
        self.rotate_right_act.setIcon(material_icon("rotate_right"))
        self.rotate_right_act.setToolTip("Rotate the selected page(s) 90° clockwise")
        self.rotate_right_act.triggered.connect(lambda *_: self.rotate_selected(90))
        self.extract_pages_act = QAction("Extract Selected...", self)
        self.extract_pages_act.setIcon(material_icon("file_copy"))
        self.extract_pages_act.setShortcut("Ctrl+Shift+E")
        self.extract_pages_act.setShortcutContext(Qt.ApplicationShortcut)
        self.extract_pages_act.setToolTip("Save the selected page(s) to a new file")
        self.extract_pages_act.triggered.connect(self.extract_selected)
        self.remove_pages_act = QAction("Remove Selected", self)
        self.remove_pages_act.setIcon(material_icon("delete", "#ffb9b9"))
        self.remove_pages_act.setToolTip("Remove the selected page(s) (Delete)")
        # Delete/Backspace remove the selected thumbnails, but only while the
        # pages strip has focus, so they never interfere with text editing.
        self.remove_pages_act.setShortcuts(
            [QKeySequence(Qt.Key_Delete), QKeySequence(Qt.Key_Backspace)]
        )
        self.remove_pages_act.setShortcutContext(Qt.WidgetWithChildrenShortcut)
        self.remove_pages_act.triggered.connect(self.remove_selected)

        self.login_act = QAction("Sign in with Google", self)
        self.login_act.setIcon(material_icon("login"))
        self.login_act.setToolTip("Sign in to Google to enable free OCR")
        self.login_act.triggered.connect(self.login)
        self.logout_act = QAction("Sign out", self)
        self.logout_act.setIcon(material_icon("logout"))
        self.logout_act.setToolTip("Sign out and remove the stored Google token")
        self.logout_act.triggered.connect(self.logout)
        self.copy_data_act = QAction("Copy Data Folder Path", self)
        self.copy_data_act.setIcon(material_icon("content_copy"))
        self.copy_data_act.setToolTip("Copy the path to Lexo's data folder (logs, config)")
        self.copy_data_act.triggered.connect(self.copy_data_path)
        self.check_update_act = QAction("Check for Updates...", self)
        self.check_update_act.setIcon(material_icon("system_update_alt"))
        self.check_update_act.setToolTip("Check PyPI for a newer version of Lexo")
        self.check_update_act.triggered.connect(self.check_for_updates)
        self.cleanup_cache_act = QAction("Clean Up Temporary Files...", self)
        self.cleanup_cache_act.setIcon(material_icon("delete_sweep"))
        self.cleanup_cache_act.setToolTip("Remove leftover working files from previous sessions")
        self.cleanup_cache_act.triggered.connect(self.cleanup_cache)
        self.about_act = QAction("About Lexo", self)
        self.about_act.setIcon(material_icon("info"))
        self.about_act.setShortcut("F1")
        self.about_act.setToolTip("Version, license, and project links")
        self.about_act.triggered.connect(self.show_about)

    def _build_menus(self) -> None:
        file_menu = self.menuBar().addMenu("&File")
        file_menu.addAction(self.open_act)
        file_menu.addAction(self.open_set_act)
        file_menu.addSeparator()
        file_menu.addAction(self.save_act)
        file_menu.addAction(self.save_as_act)
        file_menu.addAction(self.export_act)
        file_menu.addSeparator()
        file_menu.addAction(self.close_act)
        file_menu.addAction(self.exit_act)

        process_menu = self.menuBar().addMenu("&Process")
        process_menu.addAction(self.run_act)
        process_menu.addAction(self.cancel_act)
        process_menu.addAction(self.retry_failed_act)
        process_menu.addSeparator()
        process_menu.addAction(self.move_up_act)
        process_menu.addAction(self.move_down_act)
        process_menu.addAction(self.rotate_left_act)
        process_menu.addAction(self.rotate_right_act)
        process_menu.addSeparator()
        process_menu.addAction(self.extract_pages_act)
        process_menu.addAction(self.remove_pages_act)

        self.view_menu = self.menuBar().addMenu("&View")
        account_menu = self.menuBar().addMenu("&Account")
        self.account_status_act = QAction("Checking sign-in...", self)
        self.account_status_act.setIcon(material_icon("account_circle"))
        self.account_status_act.setEnabled(False)
        account_menu.addAction(self.account_status_act)
        account_menu.addSeparator()
        account_menu.addAction(self.login_act)
        account_menu.addAction(self.logout_act)
        account_menu.addSeparator()
        account_menu.addAction(self.copy_data_act)
        # Re-check on open so the menu reflects token changes (expiry, external logout).
        account_menu.aboutToShow.connect(self._refresh_account)

        help_menu = self.menuBar().addMenu("&Help")
        help_menu.addAction(self.cleanup_cache_act)
        help_menu.addSeparator()
        help_menu.addAction(self.check_update_act)
        help_menu.addSeparator()
        help_menu.addAction(self.about_act)

    def _build_body(self) -> None:
        self._build_pages_dock()
        self._build_work_surface()

        self.empty_import_panel = WelcomePanel(self.open_act, self.open_set_act, self)

        self.central_stack = QStackedWidget()
        self.central_stack.addWidget(self.empty_import_panel)
        self.central_stack.addWidget(self.work_surface)
        self.central_stack.setCurrentWidget(self.empty_import_panel)
        self.setCentralWidget(self.central_stack)

    def _build_pages_dock(self) -> None:
        self.pages = QListWidget()
        self.pages.setIconSize(QSize(92, 124))
        self.pages.setSelectionMode(QListWidget.ExtendedSelection)
        self.pages.currentRowChanged.connect(self.show_page)
        self.pages.itemSelectionChanged.connect(self._on_pages_selection)
        self.pages.setContextMenuPolicy(Qt.CustomContextMenu)
        self.pages.customContextMenuRequested.connect(self._pages_context_menu)
        self.pages.setViewMode(QListWidget.IconMode)
        self.pages.setFlow(QListWidget.LeftToRight)
        self.pages.setWrapping(True)
        self.pages.setResizeMode(QListWidget.Adjust)
        self.pages.setMovement(QListWidget.Static)
        self.pages.setGridSize(QSize(108, 152))
        self.pages.setItemDelegate(_NoFocusDelegate(self.pages))
        # Allow shrinking to a single column; the dock just opens at two columns
        # by default (see _restore_window_state in shell).
        self.pages.setMinimumWidth(120)
        # Delete/Backspace on the focused pages strip remove the selected pages.
        self.pages.addAction(self.remove_pages_act)

        self.page_count_label = QLabel("No document")
        header = QHBoxLayout()
        header.addWidget(self.page_count_label)
        header.addStretch(1)

        container = QWidget()
        column = QVBoxLayout(container)
        column.setContentsMargins(4, 4, 4, 4)
        column.setSpacing(4)
        column.addLayout(header)
        column.addWidget(self.pages)

        self.pages_dock = QDockWidget("Pages", self)
        self.pages_dock.setObjectName("PagesDock")
        self.pages_dock.setWidget(container)
        self.addDockWidget(Qt.LeftDockWidgetArea, self.pages_dock)
        self.pages_act = self.pages_dock.toggleViewAction()
        self.pages_act.setShortcut("F9")
        self.pages_act.setShortcutContext(Qt.ApplicationShortcut)
        self.pages_act.setToolTip("Show or hide the page thumbnails (F9)")
        self._add_view_toggle_action(self.pages_act, "Pages")

    def _build_work_surface(self) -> None:
        self.preview = PreviewLabel()
        self.preview.clear_image("Open a document to preview pages")
        self.preview.page_step.connect(self._step_page)
        self.preview.zoom_changed.connect(self._set_zoom_label)
        self.preview_scroll = PreviewScrollArea()
        self.preview_scroll.setWidget(self.preview)
        self.preview_scroll.setWidgetResizable(False)
        self.preview_scroll.setAlignment(Qt.AlignCenter)
        self.preview_scroll.resized.connect(self.preview.set_viewport_size)
        self.prev_act = QAction("", self)
        self.prev_act.setIcon(material_icon("chevron_left", size=22))
        self.prev_act.setToolTip("Previous page (Ctrl+PgUp)")
        self.prev_act.setShortcut("Ctrl+PgUp")
        self.prev_act.setShortcutContext(Qt.ApplicationShortcut)
        self.prev_act.triggered.connect(self.go_prev)
        self.page_nav_label = QLabel("Page")
        self.page_nav_label.setObjectName("PageNavLabel")
        self.page_input = QLineEdit()
        self.page_input.setObjectName("PageNumberInput")
        self.page_input.setEnabled(False)
        self.page_input.setMaximumWidth(42)
        self.page_input.setAlignment(Qt.AlignCenter)
        self.page_input.setToolTip("Jump to page")
        self.page_input.returnPressed.connect(self._commit_page_input)
        self.page_input.editingFinished.connect(self._commit_page_input)
        self.page_total_label = QLabel("/ 0")
        self.page_total_label.setObjectName("PageNavLabel")
        self.next_act = QAction("", self)
        self.next_act.setIcon(material_icon("chevron_right", size=22))
        self.next_act.setToolTip("Next page (Ctrl+PgDown)")
        self.next_act.setShortcut("Ctrl+PgDown")
        self.next_act.setShortcutContext(Qt.ApplicationShortcut)
        self.next_act.triggered.connect(self.go_next)
        self.zoom_out_act = QAction("Zoom Out", self)
        self.zoom_out_act.setIcon(material_icon("zoom_out", size=22))
        self.zoom_out_act.setToolTip("Zoom out (Ctrl+mouse wheel)")
        self.zoom_out_act.triggered.connect(self.preview.zoom_out)
        self.zoom_in_act = QAction("Zoom In", self)
        self.zoom_in_act.setIcon(material_icon("zoom_in", size=22))
        self.zoom_in_act.setToolTip("Zoom in (Ctrl+mouse wheel)")
        self.zoom_in_act.triggered.connect(self.preview.zoom_in)
        self.zoom_fit_act = QAction("Fit Page", self)
        self.zoom_fit_act.setIcon(material_icon("fit_screen", size=22))
        self.zoom_fit_act.setToolTip("Fit page to preview")
        self.zoom_fit_act.triggered.connect(self.preview.reset_zoom)

        preview_nav = QHBoxLayout()
        preview_nav.setContentsMargins(8, 6, 8, 6)
        preview_nav.setSpacing(8)
        self.prev_btn = QToolButton()
        self.prev_btn.setDefaultAction(self.prev_act)
        self.next_btn = QToolButton()
        self.next_btn.setDefaultAction(self.next_act)
        self.zoom_out_btn = QToolButton()
        self.zoom_out_btn.setDefaultAction(self.zoom_out_act)
        self.zoom_label = QLabel(self.preview.zoom_status())
        self.zoom_label.setObjectName("PageNavLabel")
        self.zoom_label.setMinimumWidth(42)
        self.zoom_label.setAlignment(Qt.AlignCenter)
        self.zoom_in_btn = QToolButton()
        self.zoom_in_btn.setDefaultAction(self.zoom_in_act)
        self.zoom_fit_btn = QToolButton()
        self.zoom_fit_btn.setDefaultAction(self.zoom_fit_act)
        preview_nav.addWidget(self.prev_btn)
        preview_nav.addWidget(self.page_nav_label)
        preview_nav.addWidget(self.page_input)
        preview_nav.addWidget(self.page_total_label)
        preview_nav.addWidget(self.next_btn)
        preview_nav.addStretch(1)
        preview_nav.addWidget(self.zoom_out_btn)
        preview_nav.addWidget(self.zoom_label)
        preview_nav.addWidget(self.zoom_in_btn)
        preview_nav.addWidget(self.zoom_fit_btn)
        preview_header = QWidget()
        preview_header.setObjectName("PaneHeader")
        preview_header.setFixedHeight(self.PANE_HEADER_HEIGHT)
        preview_header.setLayout(preview_nav)

        preview_container = QWidget()
        preview_container.setObjectName("PreviewPane")
        preview_layout = QVBoxLayout(preview_container)
        preview_layout.setContentsMargins(0, 0, 0, 0)
        preview_layout.setSpacing(0)
        preview_layout.addWidget(preview_header)
        preview_layout.addWidget(self.preview_scroll, 1)

        self.text = QPlainTextEdit()
        self.text.setObjectName("TextPreview")
        # Ensure Burmese renders even with no Myanmar font on the OS: keep the UI
        # font for Latin, fall back to the bundled Noto Sans Myanmar for Burmese.
        myanmar = myanmar_font_family()
        if myanmar:
            text_font = self.text.font()
            text_font.setFamilies([text_font.family(), myanmar])
            self.text.setFont(text_font)
        self.text.setPlaceholderText(
            "The page's text appears here for proofreading and export.\n\n"
            "Extract text layer: a digital PDF already stores selectable text. "
            "Extracting copies it instantly, with no OCR and no network.\n\n"
            "Run Google Docs OCR: scans and images are recognized with your own Google "
            "account (free, best for Burmese). Sign in under the Account menu.\n\n"
            "First-time Google Docs OCR setup needs a credentials.json from Google "
            "Cloud, placed in your config folder. See the README for the one-time "
            "steps."
        )
        self.text.textChanged.connect(self._capture_edit)

        text_container = QWidget()
        text_container.setObjectName("TextPane")
        text_layout = QVBoxLayout(text_container)
        text_layout.setContentsMargins(0, 0, 0, 0)
        text_layout.setSpacing(0)
        text_header = QHBoxLayout()
        text_header.setContentsMargins(8, 6, 8, 6)
        text_title = QLabel("Text")
        text_title.setObjectName("TextPaneTitle")
        self.copy_text_btn = QToolButton()
        self.copy_text_btn.setObjectName("CopyTextButton")
        self.copy_text_btn.setDefaultAction(self.copy_text_act)
        self.copy_text_btn.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        text_header.addWidget(text_title)
        text_header.addStretch(1)
        text_header.addWidget(self.copy_text_btn)
        text_header_widget = QWidget()
        text_header_widget.setObjectName("PaneHeader")
        text_header_widget.setFixedHeight(self.PANE_HEADER_HEIGHT)
        text_header_widget.setLayout(text_header)
        text_layout.addWidget(text_header_widget)
        text_layout.addWidget(self.text, 1)

        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(preview_container)
        splitter.addWidget(text_container)
        splitter.setSizes([760, 540])
        self.work_surface = splitter

    def _build_tune_dock(self) -> None:
        self.tune = TunePanel()
        workflow_tab = QWidget()
        workflow_layout = QVBoxLayout(workflow_tab)
        workflow_layout.setContentsMargins(8, 8, 8, 8)
        workflow_layout.setSpacing(8)

        mode_box = QGroupBox("Mode")
        mode_layout = QHBoxLayout(mode_box)
        self.mode_group = QButtonGroup(self)
        self.mode_group.setExclusive(True)
        self.extract_mode_btn = QToolButton()
        self.extract_mode_btn.setText("Text layer")
        self.extract_mode_btn.setToolTip("Extract text layer from a digital PDF")
        self.extract_mode_btn.setCheckable(True)
        self.extract_mode_btn.setChecked(True)
        self.ocr_mode_btn = QToolButton()
        self.ocr_mode_btn.setText("Google Docs OCR")
        self.ocr_mode_btn.setToolTip("Run OCR with Google Docs OCR")
        self.ocr_mode_btn.setCheckable(True)
        self.mode_group.addButton(self.extract_mode_btn)
        self.mode_group.addButton(self.ocr_mode_btn)
        self.mode_group.buttonToggled.connect(lambda *_: self._refresh())
        mode_layout.addWidget(self.extract_mode_btn)
        mode_layout.addWidget(self.ocr_mode_btn)
        workflow_layout.addWidget(mode_box)

        run_row = QHBoxLayout()
        self.run_btn = self._make_run_panel_button(self.run_act)
        self.cancel_btn = self._make_run_panel_button(self.cancel_act)
        run_row.addWidget(self.run_btn, 1)
        run_row.addWidget(self.cancel_btn, 1)
        workflow_layout.addLayout(run_row)

        progress_box = QGroupBox("Progress")
        progress_layout = QVBoxLayout(progress_box)
        progress_layout.setSpacing(6)
        self.run_progress = QProgressBar()
        self.run_progress.setRange(0, 1)
        self.run_progress.setValue(0)
        self.run_progress.setTextVisible(True)
        self.run_progress_label = QLabel("Idle")
        self.run_progress_label.setObjectName("RunProgressLabel")
        self.run_progress_label.setWordWrap(True)
        progress_layout.addWidget(self.run_progress)
        progress_layout.addWidget(self.run_progress_label)
        workflow_layout.addWidget(progress_box)

        self.retry_btn = self._make_run_panel_button(self.retry_failed_act)
        workflow_layout.addWidget(self.retry_btn)

        format_label = QLabel("Export as")
        format_label.setObjectName("ToolbarLabel")
        self.format = QComboBox()
        self.format.setToolTip("Format used by Export Text")
        for fmt, ext in EXTENSIONS.items():
            self.format.addItem(f"{fmt} ({ext})", fmt)
        self.format.setCurrentIndex(self.format.findData("text"))
        self.format.currentTextChanged.connect(lambda _: self._refresh())
        workflow_layout.addWidget(format_label)
        workflow_layout.addWidget(self.format)

        self.export_btn = self._make_run_panel_button(self.export_act)
        workflow_layout.addWidget(self.export_btn)
        workflow_layout.addStretch(1)
        self.tune.insert_tab(0, workflow_tab, "Run")

        page_range_box = QGroupBox("Run Pages")
        page_range_layout = QVBoxLayout(page_range_box)
        self.pages_field = QLineEdit()
        self.pages_field.setPlaceholderText("all, odd, even, or 1-3,7")
        self.pages_field.setToolTip(
            "Pages for the run; accepts all / odd / even or a range like 1-3,7. "
            "Selected thumbnails update as you type."
        )
        self.pages_field.textChanged.connect(self._sync_selection_from_field)
        page_range_layout.addWidget(self.pages_field)
        # Quick presets that fill the field (and so the selection) in one click.
        preset_row = QHBoxLayout()
        for label, spec in (("All", "all"), ("Odd", "odd"), ("Even", "even")):
            btn = QPushButton(label)
            btn.setToolTip(f"Run {label.lower()} pages")
            btn.clicked.connect(lambda _=False, s=spec: self.pages_field.setText(s))
            preset_row.addWidget(btn)
        page_range_layout.addLayout(preset_row)
        self.tune.insert_pages_widget(page_range_box)
        # Open on the Run tab, not Edit, so the crop box only appears once the
        # user deliberately switches to the Edit tab.
        self.tune.tabs.setCurrentIndex(0)

        self.tune.rotate_requested.connect(self.rotate_scope)
        self.tune.crop_toggled.connect(self._toggle_crop)
        self.tune.crop_margins_changed.connect(self._sync_crop_to_preview)
        self.tune.apply_crop_requested.connect(self.apply_crop)
        self.preview.crop_changed.connect(self._sync_crop_from_preview)
        self.tune.extract_requested.connect(self.extract_selected)
        self.tune.remove_requested.connect(self.remove_selected)
        self.tune.split_requested.connect(self.split_pdf)
        self.tune.split_line_toggled.connect(self._toggle_split)
        self.tune.apply_split_requested.connect(self.apply_split)
        self.tune.append_requested.connect(self.append_pdfs)
        self.tune_dock = QDockWidget("Tune", self)
        self.tune_dock.setObjectName("TuneDock")
        self.tune_dock.setWidget(self.tune)
        self.tune_dock.setMinimumWidth(360)
        self.addDockWidget(Qt.RightDockWidgetArea, self.tune_dock)
        self.tune_act = self.tune_dock.toggleViewAction()
        self.tune_act.setShortcut("F10")
        self.tune_act.setShortcutContext(Qt.ApplicationShortcut)
        self.tune_act.setToolTip("Show or hide the editing tools dock (F10)")
        self._add_view_toggle_action(self.tune_act, "Edit Tools")

    def _selected_mode_value(self) -> str:
        if self.ocr_mode_btn.isChecked():
            return "ocr-google"
        return "extract"

    def _build_statusbar(self) -> None:
        self.status = QStatusBar()
        self.setStatusBar(self.status)
        self.account_label = QLabel()
        self.status.addPermanentWidget(self.account_label)
        self.progress = QProgressBar()
        self.progress.setMaximumWidth(220)
        self.progress.hide()
        self.status.addPermanentWidget(self.progress)
        self.status.showMessage("Ready")
