#
# steam_library_manager/services/cloud_sync/sync_thread.py
# Background QThread wrapper for upload/download sync operations
#
# Copyright (c) 2025-2026 SwitchBros
# Licensed under the MIT License. See LICENSE for details.
#
# TODO: add cancel support for long uploads?

from __future__ import annotations

import logging

from PyQt6.QtCore import QThread, pyqtSignal

from steam_library_manager.services.cloud_sync.sync_service import CloudSyncService
from steam_library_manager.utils.i18n import t

logger = logging.getLogger(__name__)

__all__ = ["CloudSyncThread"]


class CloudSyncThread(QThread):
    """Runs upload or download in background."""

    progress_msg = pyqtSignal(str)
    finished_sync = pyqtSignal(bool, str)  # success, message/checksum

    def __init__(self, sync_service: CloudSyncService, action: str, parent=None):
        super().__init__(parent)
        self._svc = sync_service
        self._action = action  # "upload" or "download"

    def run(self) -> None:
        # dispatch to upload or download
        if self._action == "upload":
            self.progress_msg.emit(t("cloud_sync.upload_progress", current="", total=""))
            res = self._svc.upload()
        elif self._action == "download":
            self.progress_msg.emit(t("cloud_sync.download_progress"))
            res = self._svc.download()
        else:
            logger.error("unknown sync action: %s" % self._action)
            self.finished_sync.emit(False, "unknown action: %s" % self._action)
            return

        if res.success:
            logger.info("sync %s complete: %s" % (self._action, res.message))
        else:
            logger.warning("sync %s failed: %s" % (self._action, res.message))

        self.finished_sync.emit(res.success, res.message)
