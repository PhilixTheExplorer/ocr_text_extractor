"""The `MainWindow` shell: state, composition, account/help, window plumbing.

The window's behaviour is split across mixins by concern - construction
(`BuildMixin`), opening/saving (`DocumentIOMixin`), editing (`EditingMixin`),
and running (`RunMixin`). This module holds the shared state they operate on and
the cross-cutting bits (title, dirty prompt, refresh, lifecycle).
"""

from __future__ import annotations

import shutil
from typing import Any

from lexo.domain.models import ExtractedDoc, TextKind
from lexo.gui.document import WorkingDocument
from lexo.gui.qt import QApplication, QLabel, QMainWindow, QMessageBox, QPixmap, QSettings, Qt
from lexo.gui.resources import app_icon, logo_pixmap
from lexo.gui.toast import Toast
from lexo.gui.window.build import BuildMixin
from lexo.gui.window.editing import EditingMixin
from lexo.gui.window.io import DocumentIOMixin
from lexo.gui.window.run import RunMixin
from lexo.gui.worker import ProcessWorker
from lexo.infra import paths
from lexo.pipeline.engine import CancellationToken
from lexo.services import LexoService


def _format_bytes(size: int) -> str:
    value = float(size)
    for unit in ("B", "KB", "MB", "GB"):
        if value < 1024 or unit == "GB":
            return f"{value:.0f} {unit}" if unit == "B" else f"{value:.1f} {unit}"
        value /= 1024
    return f"{value:.1f} GB"


class MainWindow(QMainWindow, BuildMixin, DocumentIOMixin, EditingMixin, RunMixin):
    def __init__(self) -> None:
        super().__init__()
        self.service = LexoService.create()
        self._tmpdir = paths.new_session_tmpdir()
        self.document: WorkingDocument | None = None
        self.page_count = 0
        self.current = 0
        self.page_kinds: dict[int, TextKind] = {}
        self.page_status: dict[int, str] = {}
        self.page_texts: dict[int, str] = {}
        self.edits: dict[int, str] = {}
        self._thumb_base: dict[int, QPixmap] = {}  # base thumbnails for status badges
        self.doc: ExtractedDoc | None = None  # last extract/OCR result
        self.worker: ProcessWorker | None = None
        self.edit_worker: Any = None  # background page-edit thread (EditWorker)
        self._pending_move: tuple[list[int], set[int]] = ([], set())
        self.token: CancellationToken | None = None
        self._cancelling = False
        self.run_total = 0
        self.run_done = 0
        self.run_failed = 0

        self.setWindowIcon(app_icon())
        self._build_actions()
        self._build_menus()
        self._build_body()
        self._build_tune_dock()
        self._build_statusbar()
        self._toast = Toast(self)
        restored = self._restore_window_state()
        if not restored:
            # First run: a sensible normal size for when the window is un-maximized,
            # then open maximized to fill the screen.
            self.resize(1320, 860)
            # Open the pages strip at two thumbnail columns; it stays draggable.
            self.resizeDocks([self.pages_dock], [2 * 108 + 28], Qt.Horizontal)
            self.setWindowState(self.windowState() | Qt.WindowMaximized)
        self._update_title()
        self._refresh_account()
        self._refresh()

    # account / help

    def _refresh_account(self) -> None:
        from lexo.infra import auth_google

        signed_in = auth_google.is_authenticated()
        self.account_status_act.setText("Signed in to Google" if signed_in else "Not signed in")
        self.login_act.setText("Re-sign in with Google" if signed_in else "Sign in with Google")
        self.login_act.setEnabled(True)
        self.logout_act.setEnabled(signed_in)
        self.account_label.setText("Google: signed in" if signed_in else "Google: not signed in")

    def login(self) -> bool:
        """Run the Google sign-in flow. Returns True only on a fresh successful
        sign-in, so callers can safely retry an action that needed auth."""
        from lexo.infra import auth_google

        try:
            auth_google.login()
        except Exception as exc:
            QMessageBox.critical(self, "Sign in failed", str(exc))
            return False
        self._refresh_account()
        self.status.showMessage("Signed in with Google")
        return True

    def logout(self) -> None:
        from lexo.infra import auth_google

        auth_google.logout()
        self._refresh_account()
        self.status.showMessage("Signed out")

    def copy_data_path(self) -> None:
        from lexo.infra import paths

        QApplication.clipboard().setText(str(paths.data_dir()))
        self.notify("Data folder path copied")

    def check_for_updates(self) -> None:
        from lexo.update import UpdateCheckError, check_update_available

        self.status.showMessage("Checking for updates...")
        try:
            status = check_update_available()
        except UpdateCheckError as exc:
            QMessageBox.warning(self, "Update check failed", str(exc))
            self.status.showMessage("Update check failed")
            return

        if status.update_available:
            QMessageBox.information(
                self,
                "Update available",
                (
                    f"Lexo {status.latest_version} is available.\n"
                    f"You are running {status.current_version}.\n\n"
                    f"{status.package_url}"
                ),
            )
            self.status.showMessage(f"Update available: Lexo {status.latest_version}")
        else:
            QMessageBox.information(
                self,
                "Lexo is up to date",
                f"You are running the latest version ({status.current_version}).",
            )
            self.status.showMessage("Lexo is up to date")

    def show_about(self) -> None:
        import platform

        from lexo import __version__

        runtime = f"Python {platform.python_version()}"
        try:
            from PySide6 import __version__ as pyside_version
            from PySide6.QtCore import qVersion

            runtime += f" · Qt {qVersion()} · PySide6 {pyside_version}"
        except Exception:
            pass

        repo = "https://github.com/PhilixTheExplorer/lexo"
        body = (
            "<div style='text-align:center;'>"
            f"<h3 style='margin:0;'>Lexo {__version__}</h3>"
            "<p style='margin:3px 0;color:#9aa7b4;'>"
            "<b>L</b>ocal <b>EX</b>traction and <b>O</b>CR"
            "</p>"
            "<p style='margin:6px 0;'>Local-first desktop document OCR, Burmese-first.</p>"
            "</div>"
            "<table cellspacing='0' cellpadding='3'>"
            "<tr><td><b>OCR engine</b></td><td>Google Docs OCR (your own account)</td></tr>"
            "<tr><td><b>License</b></td><td>AGPL-3.0</td></tr>"
            f"<tr><td><b>Runtime</b></td><td>{runtime}</td></tr>"
            f"<tr><td><b>Project</b></td><td><a href='{repo}'>{repo.removeprefix('https://')}</a></td></tr>"
            "</table>"
        )

        box = QMessageBox(self)
        box.setWindowTitle("About Lexo")
        box.setTextFormat(Qt.RichText)
        box.setText(body)
        logo = logo_pixmap()
        if not logo.isNull():
            box.setIconPixmap(logo.scaled(96, 96, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        # Make the project link clickable (open in the user's browser).
        for label in box.findChildren(QLabel):
            label.setOpenExternalLinks(True)
        box.exec()

    # feedback

    def notify(self, text: str) -> None:
        """Confirm an action in both the status bar and a brief floating toast."""
        self.status.showMessage(text)
        self._toast.show_message(text)

    # window plumbing

    def _page_item_text(self, index: int) -> str:
        return f"Page {index + 1}"

    def _set_page_status(self, index: int, status: str) -> None:
        self.page_status[index] = status
        item = self.pages.item(index)
        base = self._thumb_base.get(index)
        if item is not None and base is not None:
            item.setIcon(self._decorate_thumb(base, status))

    def _stem(self) -> str:
        return self.document.source.stem if self.document else "document"

    def _title(self) -> str:
        if self.document is None:
            return "No document"
        if self.document.is_image_set:
            return f"{self._stem()} + {len(self.document.work_images) - 1} more"
        return self.document.source.name

    def _update_title(self) -> None:
        if self.document is None:
            self.setWindowTitle("Lexo")
            return
        mark = " *" if self.document.dirty else ""
        self.setWindowTitle(f"Lexo - {self._title()}{mark}")

    def _confirm_discard(self) -> bool:
        if self.document is None or not self.document.dirty:
            return True
        answer = QMessageBox.question(
            self,
            "Unsaved changes",
            "Discard unsaved edits to the current document?",
            QMessageBox.Discard | QMessageBox.Cancel,
        )
        return answer == QMessageBox.Discard

    def closeEvent(self, event: Any) -> None:
        if not self._confirm_discard():
            event.ignore()
            return
        # Stop and wait for any running OCR/extract thread before teardown, so the
        # QThread is never destroyed while still running.
        if self.worker is not None:
            if self.token is not None:
                self.token.cancel()
            self.worker.blockSignals(True)
            self.worker.wait()
        # A page edit can't be cancelled mid-flight; just wait it out so its
        # QThread is gone before we drop the working files.
        if self.edit_worker is not None:
            self.edit_worker.blockSignals(True)
            self.edit_worker.wait()
        self._save_window_state()
        shutil.rmtree(self._tmpdir, ignore_errors=True)
        super().closeEvent(event)

    def cleanup_cache(self) -> None:
        """Remove leftover working folders from previous/crashed sessions."""
        stale = paths.stale_session_tmpdirs(self._tmpdir)
        if not stale:
            QMessageBox.information(self, "Clean Up", "No leftover temporary files were found.")
            return
        total = sum(paths.dir_size(directory) for directory in stale)
        answer = QMessageBox.question(
            self,
            "Clean Up Temporary Files",
            f"Remove {len(stale)} leftover working folder(s) "
            f"({_format_bytes(total)}) from previous sessions?\n\n"
            "Close any other open Lexo windows first so their files are not removed.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.Yes,
        )
        if answer != QMessageBox.Yes:
            return
        removed, freed = paths.purge_session_tmpdirs(self._tmpdir)
        QMessageBox.information(
            self, "Clean Up", f"Removed {removed} folder(s) and freed {_format_bytes(freed)}."
        )
        self.status.showMessage(f"Cleaned up {removed} folder(s), freed {_format_bytes(freed)}")

    def _settings(self) -> QSettings:
        return QSettings("Lexo", "Lexo")

    def _restore_window_state(self) -> bool:
        """Restore saved geometry/state. Returns True if a saved size was applied."""
        settings = self._settings()
        geometry = settings.value("window/geometry")
        restored = geometry is not None
        if geometry is not None:
            self.restoreGeometry(geometry)
        state = settings.value("window/state")
        if state is not None:
            self.restoreState(state)
        splitter = settings.value("window/splitter")
        if splitter is not None:
            self.work_surface.restoreState(splitter)
        mode = settings.value("workflow/mode", "extract")
        self.ocr_mode_btn.setChecked(mode == "ocr-google")
        self.extract_mode_btn.setChecked(mode != "ocr-google")
        fmt = settings.value("workflow/export_format", "text")
        index = self.format.findData(str(fmt))
        if index >= 0:
            self.format.setCurrentIndex(index)
        return restored

    def _save_window_state(self) -> None:
        settings = self._settings()
        settings.setValue("window/geometry", self.saveGeometry())
        settings.setValue("window/state", self.saveState())
        settings.setValue("window/splitter", self.work_surface.saveState())
        settings.setValue("workflow/mode", self._selected_mode_value())
        settings.setValue("workflow/export_format", self.format.currentData())

    def _refresh(self) -> None:
        has_doc = self.page_count > 0
        busy = self.worker is not None or self.edit_worker is not None
        is_pdf = self.document.is_pdf if self.document else False
        editable = has_doc and not busy
        if hasattr(self, "extract_mode_btn"):
            mode = self._selected_mode_value()
            action_text = "Extract Text" if mode == "extract" else "Run OCR"
            self.run_act.setText(action_text)
        export_text = f"Export {self.format.currentText()}" if hasattr(self, "format") else "Export"
        self.export_act.setText(export_text)
        self.run_act.setEnabled(has_doc and not busy)
        # Only an OCR/extract run is cancellable; a page edit is not, so the Cancel
        # control tracks the run worker, not the general busy state.
        ocr_busy = self.worker is not None
        self.cancel_act.setEnabled(ocr_busy and not self._cancelling)
        self.cancel_act.setVisible(ocr_busy)
        self.close_act.setEnabled(has_doc and not busy)
        has_failed = self.doc is not None and bool(self.doc.failed_pages)
        self.retry_failed_act.setEnabled(has_failed and not busy)
        self.retry_failed_act.setVisible(has_failed)
        self.save_act.setEnabled(has_doc and not busy)
        self.save_as_act.setEnabled(has_doc and not busy)
        self.export_act.setEnabled(self.doc is not None and not busy)
        self.extract_mode_btn.setEnabled(not busy)
        self.ocr_mode_btn.setEnabled(not busy)
        self.pages_field.setEnabled(not busy)
        self.format.setEnabled(not busy)
        self.prev_act.setEnabled(has_doc and not busy and self.current > 0)
        self.next_act.setEnabled(has_doc and not busy and self.current < self.page_count - 1)
        self.zoom_out_act.setEnabled(has_doc and not busy)
        self.zoom_in_act.setEnabled(has_doc and not busy)
        self.zoom_fit_act.setEnabled(has_doc and not busy)
        self.page_input.setEnabled(has_doc and not busy)
        # Page operations (menu + pages-strip context menu) must not start another
        # edit while one is running, or during an OCR run.
        for act in (
            self.move_up_act,
            self.move_down_act,
            self.rotate_left_act,
            self.rotate_right_act,
            self.extract_pages_act,
            self.remove_pages_act,
        ):
            act.setEnabled(editable)
        self.tune.set_state(editable, is_pdf)
        if hasattr(self, "central_stack"):
            self.central_stack.setCurrentWidget(
                self.work_surface if has_doc else self.empty_import_panel
            )
