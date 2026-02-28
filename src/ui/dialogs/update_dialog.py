"""Update dialog for displaying available updates and managing downloads.

Shows version info, release notes, download progress, and handles
the save-before-restart flow for AppImage self-updates.
"""

from __future__ import annotations

import logging

from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

from src.services.update_service import UpdateInfo, UpdateService
from src.ui.widgets.ui_helper import UIHelper
from src.ui.widgets.base_dialog import BaseDialog
from src.utils.i18n import t
from src.utils.open_url import open_url
from src.version import __version__

__all__ = ["UpdateDialog"]

logger = logging.getLogger("steamlibmgr.update")


class UpdateDialog(BaseDialog):
    """Dialog showing update information with download and install controls.

    Args:
        parent: Parent widget (MainWindow).
        info: UpdateInfo with version, URL, size, notes.
        update_service: Shared UpdateService instance.
    """

    def __init__(
        self,
        parent: QWidget | None,
        info: UpdateInfo,
        update_service: UpdateService,
    ) -> None:
        self._info = info
        self._update_service = update_service
        self._downloaded_path: str | None = None
        super().__init__(
            parent=parent,
            title_key="update.dialog_title",
            min_width=550,
            buttons="custom",
        )

    def _build_content(self, content_area: QVBoxLayout) -> None:
        """Build dialog content with version info, notes, and controls."""
        # Version labels
        current_label = QLabel(t("update.current_version", version=__version__))
        new_label = QLabel(t("update.new_version", version=self._info.version))
        new_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        content_area.addWidget(current_label)
        content_area.addWidget(new_label)

        # Download size
        size_mb = self._info.download_size / (1024 * 1024)
        size_label = QLabel(t("update.download_size", size=f"{size_mb:.1f} MB"))
        content_area.addWidget(size_label)

        content_area.addSpacing(10)

        # Release notes
        notes_header = QLabel(t("update.release_notes"))
        notes_header.setStyleSheet("font-weight: bold;")
        content_area.addWidget(notes_header)

        self._notes_browser = QTextBrowser()
        self._notes_browser.setMarkdown(self._info.release_notes)
        self._notes_browser.setMinimumHeight(200)
        self._notes_browser.setOpenExternalLinks(False)
        self._notes_browser.anchorClicked.connect(lambda url: open_url(url.toString()))
        content_area.addWidget(self._notes_browser)

        # Progress bar (hidden initially)
        self._progress_bar = QProgressBar()
        self._progress_bar.setVisible(False)
        self._progress_bar.setTextVisible(True)
        content_area.addWidget(self._progress_bar)

        self._status_label = QLabel("")
        self._status_label.setVisible(False)
        content_area.addWidget(self._status_label)

        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        self._skip_btn = QPushButton(t("update.skip_version"))
        self._skip_btn.clicked.connect(self._on_skip_clicked)
        btn_layout.addWidget(self._skip_btn)

        self._action_btn = QPushButton(t("update.download_install"))
        self._action_btn.setDefault(True)
        self._action_btn.clicked.connect(self._on_action_clicked)
        btn_layout.addWidget(self._action_btn)

        content_area.addLayout(btn_layout)

        # Connect update service signals
        self._update_service.download_progress.connect(self._on_progress)
        self._update_service.download_finished.connect(self._on_download_finished)
        self._update_service.download_failed.connect(self._on_download_failed)

    def _on_action_clicked(self) -> None:
        """Handle download/install button click."""
        if self._downloaded_path:
            self._on_restart_clicked()
        else:
            self._start_download()

    def _start_download(self) -> None:
        """Start downloading the update."""
        self._action_btn.setEnabled(False)
        self._skip_btn.setEnabled(False)
        self._progress_bar.setVisible(True)
        self._progress_bar.setRange(0, self._info.download_size)
        self._status_label.setVisible(True)
        self._status_label.setText(t("update.downloading", percent="0"))
        self._update_service.download_update(self._info)

    def _on_progress(self, received: int, total: int) -> None:
        """Update progress bar during download."""
        self._progress_bar.setValue(received)
        if total > 0:
            percent = int(received * 100 / total)
            self._status_label.setText(t("update.downloading", percent=str(percent)))

    def _on_download_finished(self, path: str) -> None:
        """Handle successful download."""
        self._downloaded_path = path
        self._status_label.setText(t("update.ready_to_install"))
        self._action_btn.setText(t("update.restart_now"))
        self._action_btn.setEnabled(True)
        self._skip_btn.setEnabled(True)

    def _on_download_failed(self, error: str) -> None:
        """Handle download failure."""
        self._status_label.setText(error)
        self._action_btn.setText(t("update.download_install"))
        self._action_btn.setEnabled(True)
        self._skip_btn.setEnabled(True)
        self._progress_bar.setVisible(False)

    def _on_restart_clicked(self) -> None:
        """Save application state, then install update and restart.

        This is the ONLY place where install_update() is called.
        Save flow runs BEFORE os.execv().
        """
        if not UIHelper.confirm(
            self,
            t("update.confirm_restart"),
            title=t("update.dialog_title"),
        ):
            return

        # Save application state via MainWindow
        mw = self.parent()
        if hasattr(mw, "game_manager") and mw.game_manager:
            try:
                mw.game_manager.save_to_cloud()
            except Exception as e:
                logger.warning("Pre-update save failed: %s", e)

        self.accept()

        if not UpdateService.install_update(self._downloaded_path):
            UIHelper.show_error(mw, t("update.install_failed"))

    def _on_skip_clicked(self) -> None:
        """Skip this version and close dialog."""
        from src.config import config

        config.UPDATE_SKIPPED_VERSION = self._info.version
        config.save()
        self.reject()

    def reject(self) -> None:
        """Cancel download if in progress."""
        self._update_service.cancel_download()
        super().reject()
