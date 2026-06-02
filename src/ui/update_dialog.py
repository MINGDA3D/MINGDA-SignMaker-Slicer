"""Update notification and installer download dialog."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QThread, Qt, QUrl, Signal
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
)

from src.business.update_manager import (
    UpdateInfo,
    UpdateManager,
)
from src.ui.update_messages import format_update_file_size, translate_update_error


class UpdateDownloadWorker(QThread):
    """Download an installer on a worker thread."""

    progress_changed = Signal(int, int)
    finished_path = Signal(object)
    error_occurred = Signal(str)

    def __init__(self, manager: UpdateManager, update_info: UpdateInfo, parent=None):
        super().__init__(parent)
        self._manager = manager
        self._update_info = update_info

    def run(self):
        try:
            installer_path = self._manager.download_installer(
                self._update_info,
                progress_callback=self._emit_progress,
            )
            self.finished_path.emit(installer_path)
        except Exception as exc:
            self.error_occurred.emit(str(exc))

    def _emit_progress(self, downloaded: int, total: int):
        self.progress_changed.emit(downloaded, total)


class UpdateDialog(QDialog):
    """Prompt the user to download and install a selected update."""

    install_requested = Signal(object)

    def __init__(
        self,
        update_info: UpdateInfo,
        update_manager: UpdateManager,
        parent=None,
    ):
        super().__init__(parent)
        self._update_info = update_info
        self._update_manager = update_manager
        self._download_worker: UpdateDownloadWorker | None = None
        self._installer_path: Path | None = None

        self.setWindowTitle(self.tr("Update Available"))
        self.setModal(True)
        self.setMinimumWidth(520)

        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        title = QLabel(
            self.tr("A new version of MINGDA SignMaker is available.")
        )
        title.setWordWrap(True)
        title.setStyleSheet("font-size: 16px; font-weight: 600;")
        layout.addWidget(title)

        layout.addWidget(QLabel(
            self.tr("Current version: {version}").format(
                version=update_info.current_version,
            )
        ))
        layout.addWidget(QLabel(
            self.tr("New version: {version}").format(version=update_info.version)
        ))
        layout.addWidget(QLabel(
            self.tr("Installer size: {size}").format(
                size=format_update_file_size(update_info.asset.size_bytes),
            )
        ))

        notes = QTextEdit()
        notes.setReadOnly(True)
        notes.setPlainText(
            update_info.notes or self.tr("No release notes provided.")
        )
        notes.setMinimumHeight(130)
        layout.addWidget(notes)

        self._status_label = QLabel("")
        self._status_label.setWordWrap(True)
        layout.addWidget(self._status_label)

        self._progress_bar = QProgressBar()
        self._progress_bar.setVisible(False)
        layout.addWidget(self._progress_bar)

        button_layout = QHBoxLayout()
        button_layout.addStretch(1)

        self._open_release_button = QPushButton(self.tr("Open Release Page"))
        self._open_release_button.clicked.connect(self._open_release_page)
        self._open_release_button.setEnabled(bool(update_info.release_url))
        button_layout.addWidget(self._open_release_button)

        self._later_button = QPushButton(self.tr("Later"))
        self._later_button.clicked.connect(self.reject)
        button_layout.addWidget(self._later_button)

        self._download_button = QPushButton(self.tr("Download"))
        self._download_button.clicked.connect(self._start_download)
        button_layout.addWidget(self._download_button)

        self._run_installer_button = QPushButton(self.tr("Run Installer and Exit"))
        self._run_installer_button.setVisible(False)
        self._run_installer_button.clicked.connect(self._request_install)
        button_layout.addWidget(self._run_installer_button)

        layout.addLayout(button_layout)

    def _open_release_page(self):
        if self._update_info.release_url:
            QDesktopServices.openUrl(QUrl(self._update_info.release_url))

    def _start_download(self):
        if self._download_worker and self._download_worker.isRunning():
            return

        self._set_downloading(True)
        self._status_label.setText(self.tr("Downloading update installer..."))
        self._download_worker = UpdateDownloadWorker(
            self._update_manager,
            self._update_info,
            self,
        )
        self._download_worker.progress_changed.connect(self._on_progress_changed)
        self._download_worker.finished_path.connect(self._on_download_finished)
        self._download_worker.error_occurred.connect(self._on_download_error)
        self._download_worker.start()

    def _set_downloading(self, downloading: bool):
        self._download_button.setEnabled(not downloading)
        self._later_button.setEnabled(not downloading)
        self._open_release_button.setEnabled(
            not downloading and bool(self._update_info.release_url)
        )
        self._progress_bar.setVisible(downloading)
        if downloading:
            self._progress_bar.setRange(0, 0)
            self._progress_bar.setValue(0)

    def _on_progress_changed(self, downloaded: int, total: int):
        if total > 0:
            self._progress_bar.setRange(0, 100)
            self._progress_bar.setValue(min(100, int(downloaded * 100 / total)))
            self._status_label.setText(
                self.tr("Downloading update installer... {downloaded} / {total}").format(
                    downloaded=format_update_file_size(downloaded),
                    total=format_update_file_size(total),
                )
            )
        else:
            self._progress_bar.setRange(0, 0)
            self._status_label.setText(
                self.tr("Downloading update installer... {downloaded}").format(
                    downloaded=format_update_file_size(downloaded),
                )
            )

    def _on_download_finished(self, installer_path: object):
        self._set_downloading(False)
        self._installer_path = Path(installer_path)
        self._progress_bar.setRange(0, 100)
        self._progress_bar.setValue(100)
        self._progress_bar.setVisible(True)
        self._status_label.setText(
            self.tr("Update installer downloaded and verified.")
        )
        self._download_button.setVisible(False)
        self._run_installer_button.setVisible(True)
        self._run_installer_button.setFocus(Qt.FocusReason.OtherFocusReason)

    def _on_download_error(self, message: str):
        self._set_downloading(False)
        self._progress_bar.setVisible(False)
        self._status_label.setText(self.tr("Update download failed."))
        QMessageBox.warning(
            self,
            self.tr("Update Download Failed"),
            translate_update_error(message),
        )

    def _request_install(self):
        if self._installer_path is None:
            return
        answer = QMessageBox.question(
            self,
            self.tr("Run Installer"),
            self.tr(
                "The installer will start and MINGDA SignMaker will close. Continue?"
            ),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.Yes,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        self.install_requested.emit(self._installer_path)
        self.accept()
