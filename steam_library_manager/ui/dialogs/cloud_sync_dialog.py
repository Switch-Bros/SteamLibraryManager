#
# steam_library_manager/ui/dialogs/cloud_sync_dialog.py
# Quick cloud sync dialog opened from the toolbar button
#
# Copyright (c) 2025-2026 SwitchBros
# Licensed under the MIT License. See LICENSE for details.
#
# TODO: wire upload/download to actual SyncService calls

from __future__ import annotations

from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
)

from steam_library_manager.config import config
from steam_library_manager.ui.widgets.base_dialog import BaseDialog
from steam_library_manager.utils.i18n import t

__all__ = ["CloudSyncDialog"]

UPLOAD = 1
DOWNLOAD = 2


class CloudSyncDialog(BaseDialog):
    # compact toolbar dialog for quick cloud upload/download

    UPLOAD = UPLOAD
    DOWNLOAD = DOWNLOAD

    def __init__(self, parent=None):
        super().__init__(
            parent=parent,
            title_key="cloud_sync.toolbar_title",
            min_width=360,
            show_title_label=True,
            buttons="none",
        )

    def _build_content(self, layout):
        # cloud icon + status
        prov = getattr(config, "CLOUD_PROVIDER", "") or ""
        connected = bool(prov and prov != "none")

        self.status_label = QLabel()
        if connected:
            self.status_label.setText(
                "%s %s - %s"
                % (
                    t("emoji.cloud"),
                    prov.upper(),
                    t("cloud_sync.status_connected"),
                )
            )
        else:
            self.status_label.setText("%s %s" % (t("emoji.cloud"), t("cloud_sync.not_connected")))
        layout.addWidget(self.status_label)

        # last sync info
        last = getattr(config, "CLOUD_LAST_SYNC", "") or ""
        lbl_last = QLabel()
        if last:
            lbl_last.setText(t("cloud_sync.last_sync").replace("{time}", str(last)))
        else:
            lbl_last.setText(t("cloud_sync.last_sync_never"))
        layout.addWidget(lbl_last)

        # no-provider hint when nothing configured
        if not connected:
            hint = QLabel(t("cloud_sync.no_provider"))
            hint.setWordWrap(True)
            layout.addWidget(hint)

        # upload / download buttons
        btn_row = QHBoxLayout()
        btn_row.addStretch()

        self.btn_upload = QPushButton("%s %s" % (t("emoji.upload"), t("cloud_sync.upload_btn")))
        self.btn_upload.setEnabled(connected)
        self.btn_upload.setStyleSheet("QPushButton { color: #3b82f6; }")
        self.btn_upload.clicked.connect(self._on_upload)
        btn_row.addWidget(self.btn_upload)

        self.btn_download = QPushButton("%s %s" % (t("emoji.download"), t("cloud_sync.download_btn")))
        self.btn_download.setEnabled(connected)
        self.btn_download.setStyleSheet("QPushButton { color: #22c55e; }")
        self.btn_download.clicked.connect(self._on_download)
        btn_row.addWidget(self.btn_download)

        btn_row.addStretch()
        layout.addLayout(btn_row)

    def _on_upload(self):
        self.done(UPLOAD)

    def _on_download(self):
        self.done(DOWNLOAD)
