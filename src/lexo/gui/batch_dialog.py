"""Configuration dialog for multi-PDF batch OCR."""

from __future__ import annotations

from pathlib import Path

from lexo.batch import BatchOcrConfig, collect_pdf_inputs
from lexo.gui.qt import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


class BatchOcrDialog(QDialog):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Batch OCR PDFs")
        self.setMinimumWidth(560)

        self.sources: tuple[Path, ...] = ()
        self.source_summary = QLineEdit("No PDFs selected")
        self.source_summary.setReadOnly(True)
        self.output_dir = QLineEdit()
        self.lang = QLineEdit("my")
        self.force_ocr = QCheckBox("OCR every page, even if it has embedded text")
        self.force_ocr.setChecked(True)
        self.overwrite = QCheckBox("Overwrite existing TXT files")

        form = QFormLayout()
        form.addRow("PDF files", self._source_row())
        form.addRow("Output folder", self._folder_row(self.output_dir, self._browse_output))
        form.addRow("OCR language", self.lang)
        form.addRow("", self.force_ocr)
        form.addRow("", self.overwrite)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.button(QDialogButtonBox.Ok).setText("Start OCR")
        buttons.accepted.connect(self._accept_if_valid)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(buttons)

    def _source_row(self) -> QWidget:
        row = QWidget()
        layout = QHBoxLayout(row)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.source_summary)
        files_button = QPushButton("Select PDFs...")
        files_button.clicked.connect(self._browse_files)
        layout.addWidget(files_button)
        folder_button = QPushButton("Use Folder...")
        folder_button.clicked.connect(self._browse_folder)
        layout.addWidget(folder_button)
        return row

    def _folder_row(self, field: QLineEdit, handler: object) -> QWidget:
        row = QWidget()
        layout = QHBoxLayout(row)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(field)
        button = QPushButton("Browse...")
        button.clicked.connect(handler)  # type: ignore[arg-type]
        layout.addWidget(button)
        return row

    def _browse_files(self) -> None:
        filenames, _ = QFileDialog.getOpenFileNames(
            self, "Choose PDF files", "", "PDF files (*.pdf)"
        )
        if filenames:
            self._set_sources(collect_pdf_inputs(Path(name) for name in filenames))

    def _browse_folder(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Choose folder containing PDFs")
        if folder:
            try:
                sources = collect_pdf_inputs([Path(folder)])
            except ValueError as exc:
                QMessageBox.warning(self, "Batch OCR", str(exc))
                return
            self._set_sources(sources)

    def _set_sources(self, sources: tuple[Path, ...]) -> None:
        self.sources = sources
        self.source_summary.setText(f"{len(sources)} PDF file(s) selected")
        self.source_summary.setToolTip("\n".join(str(source) for source in sources))
        if not self.output_dir.text().strip():
            self.output_dir.setText(str(sources[0].parent / "txt"))

    def _browse_output(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Choose TXT output folder")
        if folder:
            self.output_dir.setText(folder)

    def _accept_if_valid(self) -> None:
        try:
            self.configuration()
        except ValueError as exc:
            QMessageBox.warning(self, "Batch OCR", str(exc))
            return
        self.accept()

    def configuration(self) -> BatchOcrConfig:
        destination = self.output_dir.text().strip()
        if not self.sources:
            raise ValueError("Choose at least one PDF.")
        if not destination:
            raise ValueError("Choose an output folder.")
        return BatchOcrConfig(
            sources=self.sources,
            output_dir=Path(destination),
            lang=self.lang.text().strip() or None,
            force_ocr=self.force_ocr.isChecked(),
            overwrite=self.overwrite.isChecked(),
        )
