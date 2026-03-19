#
# steam_library_manager/ui/dialogs/update_dialog.py
# Dialog for displaying available updates and triggering installation
#
# Copyright © 2025-2026 SwitchBros
# Licensed under the MIT License. See LICENSE for details.
#

from __future__ import annotations

import logging

from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QTextBrowser,
)

from steam_library_manager.services.update_service import UpdateService
from steam_library_manager.ui.widgets.ui_helper import UIHelper
from steam_library_manager.ui.widgets.base_dialog import BaseDialog
from steam_library_manager.utils.i18n import t
from steam_library_manager.utils.open_url import open_url
from steam_library_manager.version import __version__

__all__ = ["UpdateDialog"]

logger = logging.getLogger("steamlibmgr.update")


class UpdateDialog(BaseDialog):
    """Shows update info with download/install controls.
    Handles the full download-verify-restart flow.
    """

    def __init__(self, parent, info, update_service):
        self._info = info
        self._svc = update_service
        self._dl_path = None
        super().__init__(
            parent=parent,
            title_key="update.dialog_title",
            min_width=550,
            buttons="custom",
        )

    def _build_content(self, content_area):
        # Version labels
        cur_lbl = QLabel(t("update.current_version", version=__version__))
        new_lbl = QLabel(t("update.new_version", version=self._info.version))
        new_lbl.setStyleSheet("font-weight: bold; font-size: 14px;")
        content_area.addWidget(cur_lbl)
        content_area.addWidget(new_lbl)

        # Download size
        size_mb = self._info.download_size / (1024 * 1024)
        content_area.addWidget(QLabel(t("update.download_size", size="%.1f MB" % size_mb)))

        content_area.addSpacing(10)

        # Release notes
        hdr = QLabel(t("update.release_notes"))
        hdr.setStyleSheet("font-weight: bold;")
        content_area.addWidget(hdr)

        self._notes = QTextBrowser()
        self._notes.setMarkdown(self._info.release_notes)
        self._notes.setMinimumHeight(200)
        self._notes.setOpenExternalLinks(False)
        self._notes.anchorClicked.connect(lambda url: open_url(url.toString()))
        content_area.addWidget(self._notes)

        # Progress bar (hidden initially)
        self._bar = QProgressBar()
        self._bar.setVisible(False)
        self._bar.setTextVisible(True)
        content_area.addWidget(self._bar)

        self._status = QLabel("")
        self._status.setVisible(False)
        content_area.addWidget(self._status)

        # Buttons
        btn_row = QHBoxLayout()
        btn_row.addStretch()

        self._skip_btn = QPushButton(t("update.skip_version"))
        self._skip_btn.clicked.connect(self._on_skip)
        btn_row.addWidget(self._skip_btn)

        self._act_btn = QPushButton(t("update.download_install"))
        self._act_btn.setDefault(True)
        self._act_btn.clicked.connect(self._on_act)
        btn_row.addWidget(self._act_btn)

        content_area.addLayout(btn_row)

        # Connect update service signals
        self._svc.download_progress.connect(self._on_prog)
        self._svc.download_finished.connect(self._on_done)
        self._svc.download_failed.connect(self._on_fail)

    def _on_act(self):
        # Download or restart depending on state
        if self._dl_path:
            self._do_restart()
        else:
            self._do_download()

    def _do_download(self):
        # Kick off the download
        self._act_btn.setEnabled(False)
        self._skip_btn.setEnabled(False)
        self._bar.setVisible(True)
        self._bar.setRange(0, self._info.download_size)
        self._status.setVisible(True)
        self._status.setText(t("update.downloading", percent="0"))
        self._svc.download_update(self._info)

    def _on_prog(self, received, total):
        # Update progress bar
        self._bar.setValue(received)
        if total > 0:
            pct = int(received * 100 / total)
            self._status.setText(t("update.downloading", percent=str(pct)))

    def _on_done(self, path):
        # Download finished successfully
        self._dl_path = path
        self._status.setText(t("update.ready_to_install"))
        self._act_btn.setText(t("update.restart_now"))
        self._act_btn.setEnabled(True)
        self._skip_btn.setEnabled(True)

    def _on_fail(self, error):
        # Download failed
        self._status.setText(error)
        self._act_btn.setText(t("update.download_install"))
        self._act_btn.setEnabled(True)
        self._skip_btn.setEnabled(True)
        self._bar.setVisible(False)

    def _do_restart(self):
        # Save state, install update, restart.
        # This is the ONLY place where install_update() is called.
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
            except Exception as exc:
                logger.warning("Pre-update save failed: %s", exc)

        self.accept()

        if not UpdateService.install_update(self._dl_path):
            UIHelper.show_error(mw, t("update.install_failed"))

    def _on_skip(self):
        # Skip this version
        from steam_library_manager.config import config

        config.UPDATE_SKIPPED_VERSION = self._info.version
        config.save()
        self.reject()

    def reject(self):
        # Cancel download if running
        self._svc.cancel_download()
        super().reject()
