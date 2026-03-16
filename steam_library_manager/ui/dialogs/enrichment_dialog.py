#
# steam_library_manager/ui/dialogs/enrichment_dialog.py
# Progress dialog for background enrichment operations
#
# Copyright © 2025-2026 SwitchBros
# Licensed under the MIT License. See LICENSE for details.
#

from __future__ import annotations

from typing import TYPE_CHECKING

from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
)

from steam_library_manager.services.enrichment.enrichment_service import EnrichmentThread
from steam_library_manager.ui.utils.font_helper import FontHelper
from steam_library_manager.ui.widgets.base_dialog import BaseDialog
from steam_library_manager.ui.widgets.ui_helper import UIHelper
from steam_library_manager.utils.i18n import t
from steam_library_manager.utils.timeouts import THREAD_WAIT_MS

if TYPE_CHECKING:
    from PyQt6.QtWidgets import QWidget

__all__ = ["EnrichmentDialog"]


class EnrichmentDialog(BaseDialog):
    """Progress dialog for background enrichment operations."""

    def __init__(self, title: str, parent: QWidget | None = None) -> None:
        self._header_title = title
        self._thread: EnrichmentThread | None = None
        self.wants_force_refresh: bool = False
        super().__init__(
            parent,
            title_key="ui.enrichment.dialog_title",
            show_title_label=False,
            buttons="custom",
        )
        self.setMinimumHeight(150)

    def _build_content(self, layout: QVBoxLayout) -> None:
        title_label = QLabel(self._header_title)
        title_label.setFont(FontHelper.get_font(size=14, weight=FontHelper.BOLD))
        layout.addWidget(title_label)

        self._progress_bar = QProgressBar()
        self._progress_bar.setRange(0, 100)
        self._progress_bar.setValue(0)
        layout.addWidget(self._progress_bar)

        self._status_label = QLabel("")
        layout.addWidget(self._status_label)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        self._cancel_btn = QPushButton(t("common.cancel"))
        self._cancel_btn.clicked.connect(self._on_cancel)
        btn_layout.addWidget(self._cancel_btn)
        layout.addLayout(btn_layout)

    def start_thread(self, thread: EnrichmentThread) -> None:
        """Attaches the enrichment thread and connects signals."""
        self._thread = thread

        thread.progress.connect(self._on_progress)
        thread.finished_enrichment.connect(self._on_finished)
        thread.error.connect(self._on_error)

    def showEvent(self, event) -> None:
        super().showEvent(event)
        if self._thread and not self._thread.isRunning():
            self._thread.start()

    def _on_progress(self, step_text: str, current: int, total: int) -> None:
        if total > 0:
            percent = int((current / total) * 100)
            self._progress_bar.setValue(percent)
        self._status_label.setText(step_text)

    def _on_finished(self, success: int, failed: int) -> None:
        self._cleanup_thread()
        self.wants_force_refresh = UIHelper.show_batch_result(
            self,
            t("ui.enrichment.complete", success=success, failed=failed),
            t("ui.enrichment.complete_title"),
        )
        self.accept()

    def _on_error(self, message: str) -> None:
        self._cleanup_thread()
        UIHelper.show_warning(self, message)
        self.reject()

    def _on_cancel(self) -> None:
        """Handles the cancel button click."""
        if self._thread:
            self._thread.cancel()
        self._cancel_btn.setEnabled(False)
        self._cancel_btn.setText(t("emoji.ellipsis"))

    def _cleanup_thread(self) -> None:
        """Stops and cleans up the background thread."""
        if self._thread and self._thread.isRunning():
            self._thread.quit()
            self._thread.wait(THREAD_WAIT_MS)
        self._thread = None

    def closeEvent(self, event) -> None:
        if self._thread and self._thread.isRunning():
            self._on_cancel()
            event.ignore()
        else:
            event.accept()
