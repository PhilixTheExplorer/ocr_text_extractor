"""The "Tune" dock: document-editing controls.

Owns only the editing UI and an "apply to" scope. It does no editing itself -
it emits a request signal for each operation and exposes the chosen scope, so
the main window stays the single place that maps requests onto the document.
"""

from __future__ import annotations

from lexo.gui.icons import material_icon
from lexo.gui.qt import (
    QButtonGroup,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QRadioButton,
    QSpinBox,
    Qt,
    QTabWidget,
    QVBoxLayout,
    QWidget,
    Signal,
)

SCOPE_PAGE = "page"
SCOPE_ALL = "all"
SCOPE_SELECTED = "selected"


class TunePanel(QWidget):
    rotate_requested = Signal(int)
    crop_toggled = Signal(bool)
    crop_margins_changed = Signal()
    apply_crop_requested = Signal()
    extract_requested = Signal()
    remove_requested = Signal()
    split_requested = Signal()
    split_line_toggled = Signal(bool)
    apply_split_requested = Signal()
    append_requested = Signal()

    def __init__(self) -> None:
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)

        self.tabs = QTabWidget()
        self.tabs.setUsesScrollButtons(False)
        layout.addWidget(self.tabs)

        page_tab = QWidget()
        page_layout = QVBoxLayout(page_tab)

        scope_box = QGroupBox("Apply to")
        scope_box.setToolTip("Which pages rotate and crop apply to")
        scope_layout = QVBoxLayout(scope_box)
        self.scope_page = QRadioButton("This page")
        self.scope_page.setToolTip("Apply to the page currently shown in the preview")
        self.scope_all = QRadioButton("All pages")
        self.scope_all.setToolTip("Apply to every page in the document")
        self.scope_selected = QRadioButton("Selected pages")
        self.scope_selected.setToolTip("Apply to the thumbnails selected in the Pages strip")
        self.scope_page.setChecked(True)
        self._scope_group = QButtonGroup(self)
        for btn in (self.scope_page, self.scope_all, self.scope_selected):
            self._scope_group.addButton(btn)
            scope_layout.addWidget(btn)
        page_layout.addWidget(scope_box)

        rotate_box = QGroupBox("Rotate")
        rotate_layout = QHBoxLayout(rotate_box)
        rotate_left = QPushButton("Left 90°")
        rotate_left.setIcon(material_icon("rotate_left"))
        rotate_left.setToolTip("Rotate 90° counter-clockwise (uses the Apply-to scope)")
        rotate_left.clicked.connect(lambda: self.rotate_requested.emit(-90))
        rotate_right = QPushButton("Right 90°")
        rotate_right.setIcon(material_icon("rotate_right"))
        rotate_right.setToolTip("Rotate 90° clockwise (uses the Apply-to scope)")
        rotate_right.clicked.connect(lambda: self.rotate_requested.emit(90))
        rotate_layout.addWidget(rotate_left)
        rotate_layout.addWidget(rotate_right)
        page_layout.addWidget(rotate_box)

        crop_box = QGroupBox("Crop")
        crop_layout = QVBoxLayout(crop_box)
        self.crop_toggle = QPushButton("Draw crop box")
        self.crop_toggle.setIcon(material_icon("crop"))
        self.crop_toggle.setCheckable(True)
        self.crop_toggle.setToolTip("Show a draggable crop box on the page preview")
        self.crop_toggle.toggled.connect(self.crop_toggled.emit)

        margins = QGridLayout()
        self.crop_top = QSpinBox()
        self.crop_bottom = QSpinBox()
        self.crop_left = QSpinBox()
        self.crop_right = QSpinBox()
        self._crop_spins = (self.crop_top, self.crop_bottom, self.crop_left, self.crop_right)
        edges = ("top", "bottom", "left", "right")
        for spin, edge in zip(self._crop_spins, edges, strict=True):
            spin.setRange(0, 95)
            spin.setSuffix(" %")
            spin.setMaximumWidth(96)
            spin.setAlignment(Qt.AlignRight)
            spin.setToolTip(f"Percent to trim from the {edge}")
            spin.valueChanged.connect(lambda _=0: self.crop_margins_changed.emit())
        margins.addWidget(QLabel("Top"), 0, 0)
        margins.addWidget(self.crop_top, 0, 1)
        margins.addWidget(QLabel("Left"), 0, 2)
        margins.addWidget(self.crop_left, 0, 3)
        margins.addWidget(QLabel("Bottom"), 1, 0)
        margins.addWidget(self.crop_bottom, 1, 1)
        margins.addWidget(QLabel("Right"), 1, 2)
        margins.addWidget(self.crop_right, 1, 3)

        crop_apply = QPushButton("Apply crop")
        crop_apply.setIcon(material_icon("content_cut"))
        crop_apply.setToolTip("Trim the page(s) to the box / margins above")
        crop_apply.clicked.connect(self.apply_crop_requested.emit)
        crop_layout.addWidget(self.crop_toggle)
        crop_layout.addLayout(margins)
        crop_layout.addWidget(crop_apply)
        page_layout.addWidget(crop_box)
        page_layout.addStretch(1)
        self.tabs.addTab(page_tab, "Edit")

        pages_tab = QWidget()
        self.pages_layout_root = QVBoxLayout(pages_tab)
        pages_box = QGroupBox("Pages")
        pages_layout = QVBoxLayout(pages_box)
        extract_btn = QPushButton("Extract selected to new file...")
        extract_btn.setIcon(material_icon("file_copy"))
        extract_btn.setToolTip("Save the selected thumbnails to a new file")
        extract_btn.clicked.connect(self.extract_requested.emit)
        remove_btn = QPushButton("Remove selected pages")
        remove_btn.setObjectName("DangerButton")
        remove_btn.setIcon(material_icon("delete", "#ffb9b9"))
        remove_btn.setToolTip("Delete the selected thumbnails from this document")
        remove_btn.clicked.connect(self.remove_requested.emit)
        pages_layout.addWidget(extract_btn)
        pages_layout.addWidget(remove_btn)
        self.pages_layout_root.addWidget(pages_box)
        self.pages_layout_root.addStretch(1)
        self.tabs.addTab(pages_tab, "Pages")

        pdf_tab = QWidget()
        pdf_tab_layout = QVBoxLayout(pdf_tab)
        self._pdf_box = QGroupBox("PDF")
        pdf_layout = QVBoxLayout(self._pdf_box)
        self.split_line_toggle = QPushButton("Show split line")
        self.split_line_toggle.setIcon(material_icon("vertical_split"))
        self.split_line_toggle.setCheckable(True)
        self.split_line_toggle.setToolTip("Show a draggable line for splitting two-up spreads")
        self.split_line_toggle.toggled.connect(self.split_line_toggled.emit)
        apply_split_btn = QPushButton("Split two-up at line")
        apply_split_btn.setIcon(material_icon("content_cut"))
        apply_split_btn.setToolTip("Split each page into two at the line")
        apply_split_btn.clicked.connect(self.apply_split_requested.emit)
        split_btn = QPushButton("Split into files...")
        split_btn.setIcon(material_icon("call_split"))
        split_btn.setToolTip("Split the PDF into several files of N pages each")
        split_btn.clicked.connect(self.split_requested.emit)
        append_btn = QPushButton("Append PDF(s)...")
        append_btn.setIcon(material_icon("library_add"))
        append_btn.setToolTip("Append other PDF(s) to the end of this document")
        append_btn.clicked.connect(self.append_requested.emit)
        for btn in (self.split_line_toggle, apply_split_btn, split_btn, append_btn):
            pdf_layout.addWidget(btn)
        pdf_tab_layout.addWidget(self._pdf_box)
        pdf_tab_layout.addStretch(1)
        self.tabs.addTab(pdf_tab, "PDF")

        self._editing_widgets = [
            scope_box,
            rotate_box,
            crop_box,
            pages_box,
        ]

        # Switching to the Edit tab turns the crop box on automatically; the
        # "Draw crop box" button lets the user toggle it off/on at any time.
        self.tabs.currentChanged.connect(self._on_tab_changed)

    def _on_tab_changed(self, index: int) -> None:
        self.crop_toggle.setChecked(self.tabs.tabText(index) == "Edit")

    def scope(self) -> str:
        if self.scope_all.isChecked():
            return SCOPE_ALL
        if self.scope_selected.isChecked():
            return SCOPE_SELECTED
        return SCOPE_PAGE

    def insert_tab(self, index: int, widget: QWidget, label: str) -> None:
        self.tabs.insertTab(index, widget, label)

    def insert_pages_widget(self, widget: QWidget) -> None:
        self.pages_layout_root.insertWidget(0, widget)

    def crop_margins(self) -> tuple[float, float, float, float]:
        """Trim percentages as (top, bottom, left, right)."""
        return (
            self.crop_top.value(),
            self.crop_bottom.value(),
            self.crop_left.value(),
            self.crop_right.value(),
        )

    def set_crop_margins(self, top: float, bottom: float, left: float, right: float) -> None:
        """Set the margin fields without emitting crop_margins_changed."""
        for spin, value in zip(self._crop_spins, (top, bottom, left, right), strict=True):
            spin.blockSignals(True)
            spin.setValue(int(round(value)))
            spin.blockSignals(False)

    def reset_crop(self) -> None:
        self.crop_toggle.setChecked(False)
        self.set_crop_margins(0, 0, 0, 0)

    def reset_split(self) -> None:
        self.split_line_toggle.setChecked(False)

    def set_state(self, editable: bool, is_pdf: bool) -> None:
        for widget in self._editing_widgets:
            widget.setEnabled(editable)
        self._pdf_box.setEnabled(editable and is_pdf)
