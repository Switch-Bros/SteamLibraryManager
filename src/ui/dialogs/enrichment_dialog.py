"""Progress dialog for metadata enrichment operations.

Displays a progress bar, current game name, and cancel button
while HLTB or Steam API enrichment runs in a background thread.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from PyQt6.QtCore import QThread
from PyQt6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
)

from src.services.enrichment_service import EnrichmentWorker
from src.ui.utils.font_helper import FontHelper
from src.ui.widgets.ui_helper import UIHelper
from src.utils.i18n import t

if TYPE_CHECKING:
    from PyQt6.QtWidgets import QWidget

__all__ = ["EnrichmentDialog"]


class EnrichmentDialog(QDialog):
    """Progress dialog for background enrichment operations.

    Shows a title, progress bar, current item label, and cancel button.
    Runs the EnrichmentWorker in a dedicated QThread.

    Attributes:
        worker: The enrichment worker running in the background thread.
        thread: The QThread hosting the worker.
    """

    def __init__(self, title: str, parent: QWidget | None = None) -> None:
        """Initializes the EnrichmentDialog.

        Args:
            title: Dialog title text.
            parent: Parent widget.
        """
        super().__init__(parent)
        self.setWindowTitle(t("ui.enrichment.dialog_title"))
        self.setMinimumWidth(450)
        self.setModal(True)

        self.worker: EnrichmentWorker | None = None
        self.thread: QThread | None = None

        layout = QVBoxLayout(self)

        # Title label
        title_label = QLabel(title)
        title_label.setFont(FontHelper.get_font(size=14, weight=FontHelper.BOLD))
        layout.addWidget(title_label)

        # Progress bar
        self._progress_bar = QProgressBar()
        self._progress_bar.setRange(0, 100)
        self._progress_bar.setValue(0)
        layout.addWidget(self._progress_bar)

        # Status label
        self._status_label = QLabel("")
        layout.addWidget(self._status_label)

        # Cancel button
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        self._cancel_btn = QPushButton(t("ui.enrichment.btn_cancel"))
        self._cancel_btn.clicked.connect(self._on_cancel)
        btn_layout.addWidget(self._cancel_btn)
        layout.addLayout(btn_layout)

    def start_worker(self, worker: EnrichmentWorker, thread: QThread) -> None:
        """Attaches a worker and thread, connects signals, and starts.

        Args:
            worker: The EnrichmentWorker to monitor.
            thread: The QThread the worker runs in.
        """
        self.worker = worker
        self.thread = thread

        worker.progress.connect(self._on_progress)
        worker.finished.connect(self._on_finished)
        worker.error.connect(self._on_error)

        thread.start()

    def _on_progress(self, step_text: str, current: int, total: int) -> None:
        """Updates the progress bar and status label.

        Args:
            step_text: Description of the current step.
            current: Current progress count.
            total: Total items to process.
        """
        if total > 0:
            percent = int((current / total) * 100)
            self._progress_bar.setValue(percent)
        self._status_label.setText(step_text)

    def _on_finished(self, success: int, failed: int) -> None:
        """Shows completion summary and closes the dialog.

        Args:
            success: Number of successfully updated games.
            failed: Number of failed games.
        """
        self._cleanup_thread()
        UIHelper.show_info(
            self,
            t("ui.enrichment.complete", success=success, failed=failed),
            t("ui.enrichment.complete_title"),
        )
        self.accept()

    def _on_error(self, message: str) -> None:
        """Shows an error message and closes the dialog.

        Args:
            message: Error description.
        """
        self._cleanup_thread()
        UIHelper.show_warning(self, message)
        self.reject()

    def _on_cancel(self) -> None:
        """Handles the cancel button click."""
        if self.worker:
            self.worker.cancel()
        self._cancel_btn.setEnabled(False)
        self._cancel_btn.setText("...")

    def _cleanup_thread(self) -> None:
        """Stops and cleans up the background thread."""
        if self.thread and self.thread.isRunning():
            self.thread.quit()
            self.thread.wait(3000)
        self.thread = None
        self.worker = None

    def closeEvent(self, event) -> None:
        """Prevents closing while enrichment is running.

        Args:
            event: The close event.
        """
        if self.thread and self.thread.isRunning():
            self._on_cancel()
            event.ignore()
        else:
            event.accept()
