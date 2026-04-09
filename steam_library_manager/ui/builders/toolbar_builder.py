#
# steam_library_manager/ui/builders/toolbar_builder.py
# Main window toolbar with actions and icons
#
# Copyright © 2025-2026 SwitchBros
# Licensed under the MIT License. See LICENSE for details.
#

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import QWidget, QSizePolicy

from steam_library_manager.config import config
from steam_library_manager.ui.widgets.ui_helper import UIHelper
from steam_library_manager.utils.i18n import t

__all__ = ["ToolbarBuilder"]


class ToolbarBuilder:
    """Builds the main QToolBar."""

    def __init__(self, mw):
        self.mw = mw

    def build(self, tb):
        # populate toolbar
        tb.clear()
        tb.setMovable(False)
        tb.setFloatable(False)
        tb.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)

        # refresh
        a = QAction("%s %s" % (t("emoji.refresh"), t("menu.file.refresh")), self.mw)
        a.setToolTip(t("menu.file.refresh"))
        a.triggered.connect(self.mw.file_actions.refresh_data)
        tb.addAction(a)

        # save
        a = QAction("%s %s" % (t("emoji.disk"), t("common.save")), self.mw)
        a.setToolTip(t("common.save"))
        a.triggered.connect(self.mw.file_actions.force_save)
        tb.addAction(a)

        tb.addSeparator()

        # auto categorize
        a = QAction("%s %s" % (t("emoji.blitz"), t("menu.edit.auto_categorize")), self.mw)
        a.setToolTip(t("menu.edit.auto_categorize"))
        a.triggered.connect(self.mw.edit_actions.auto_categorize)
        tb.addAction(a)

        # bulk edit
        a = QAction("%s %s" % (t("emoji.edit"), t("menu.edit.metadata.bulk")), self.mw)
        a.setToolTip(t("menu.edit.metadata.bulk"))
        a.triggered.connect(self.mw.metadata_actions.bulk_edit_metadata)
        tb.addAction(a)

        tb.addSeparator()

        # missing metadata
        a = QAction("%s %s" % (t("emoji.search"), t("menu.edit.find_missing_metadata")), self.mw)
        a.setToolTip(t("menu.edit.find_missing_metadata"))
        a.triggered.connect(self.mw.tools_actions.find_missing_metadata)
        tb.addAction(a)

        tb.addSeparator()

        # cloud sync
        a = QAction("%s %s" % (t("emoji.cloud"), t("cloud_sync.toolbar_title")), self.mw)
        a.setToolTip(t("cloud_sync.toolbar_title"))
        a.triggered.connect(self._open_cloud_sync)
        tb.addAction(a)

        # spacer
        sp = QWidget()
        sp.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        tb.addWidget(sp)

        # settings
        a = QAction("%s %s" % (t("emoji.settings"), t("settings.title")), self.mw)
        a.setToolTip(t("settings.title"))
        a.triggered.connect(self.mw.settings_actions.show_settings)
        tb.addAction(a)

        tb.addSeparator()

        # auth section
        if self.mw.steam_username and config.STEAM_ACCESS_TOKEN:
            self._user(tb)
        else:
            self._login(tb)

    def _open_cloud_sync(self):
        from steam_library_manager.ui.dialogs.cloud_sync_dialog import (
            CloudSyncDialog,
        )

        dlg = CloudSyncDialog(self.mw)
        result = dlg.exec()

        if result in (CloudSyncDialog.UPLOAD, CloudSyncDialog.DOWNLOAD):
            self._run_cloud_sync("upload" if result == CloudSyncDialog.UPLOAD else "download")

    def _run_cloud_sync(self, action):
        from datetime import datetime

        from steam_library_manager.core.logging import logger
        from steam_library_manager.main import _create_cloud_provider
        from steam_library_manager.services.cloud_sync.sync_service import CloudSyncService
        from steam_library_manager.ui.widgets.ui_helper import UIHelper

        prov = _create_cloud_provider()
        if prov is None:
            UIHelper.show_error(self.mw, "Cloud Sync", "Connection failed")
            return

        db_path = config.DATA_DIR / "metadata.db"

        if action == "download":
            # close the DB before overwriting the file on disk
            gs = self.mw.game_service
            if gs and gs.database:
                gs.database.close()
                gs.database = None

        # upload needs existing file, download needs target path even if file doesn't exist yet
        col_path = config.get_cloud_storage_path(must_exist=(action == "upload"))

        svc = CloudSyncService(
            provider=prov,
            db_path=db_path,
            settings_path=config.SETTINGS_FILE,
            tmp_dir=config.CACHE_DIR / "cloud_sync",
            collections_path=col_path,
        )

        if action == "upload":
            res = svc.upload()
        else:
            # backup before download
            from steam_library_manager.core.backup_manager import BackupManager

            bm = BackupManager(backup_dir=config.DATA_DIR / "backups")
            if db_path.exists():
                bm.create_backup(db_path)
            res = svc.download()

        prov.disconnect()

        if res.success:
            config.CLOUD_LAST_CHECKSUM = res.message
            config.CLOUD_LAST_SYNC = datetime.now().isoformat()
            config.save()

            if action == "download":
                # DB was replaced on disk - must restart to load the new data
                UIHelper.show_success(
                    self.mw,
                    "Cloud Sync",
                    t("cloud_sync.download_success_restart"),
                )
                logger.info("Cloud sync download OK, restarting: %s" % res.message[:12])
                self.mw._stop_background_threads()
                import os
                import sys

                os.execvp(sys.executable, [sys.executable] + sys.argv)
            else:
                UIHelper.show_success(self.mw, "Cloud Sync", t("cloud_sync.upload_success"))
                logger.info("Cloud sync upload OK: %s" % res.message[:12])
        else:
            msg = (
                t("cloud_sync.upload_failed", error=res.message)
                if action == "upload"
                else t("cloud_sync.download_failed", error=res.message)
            )
            UIHelper.show_error(self.mw, "Cloud Sync", msg)
            logger.error("Cloud sync %s failed: %s" % (action, res.message))

    def _user(self, tb):
        a = QAction("%s %s" % (t("emoji.user"), self.mw.steam_username), self.mw)
        a.setToolTip(t("steam.login.logged_in_as", user=self.mw.steam_username))
        a.triggered.connect(lambda: ToolbarBuilder._dlg(self.mw))
        tb.addAction(a)

    def _login(self, tb):
        a = QAction("%s %s" % (t("emoji.login"), t("steam.login.button")), self.mw)
        a.setToolTip(t("steam.login.button"))
        a.triggered.connect(self.mw.steam_actions.start_steam_login)
        tb.addAction(a)

    @staticmethod
    def _dlg(mw):
        from PyQt6.QtWidgets import QMessageBox

        b = QMessageBox(mw)
        b.setWindowTitle(t("steam.login.steam_login_title"))
        b.setText(t("steam.login.logged_in_as", user=mw.steam_username))
        b.setIcon(QMessageBox.Icon.Information)

        b.addButton(t("common.ok"), QMessageBox.ButtonRole.AcceptRole)
        out = b.addButton(t("steam.login.logout"), QMessageBox.ButtonRole.DestructiveRole)

        b.exec()

        if b.clickedButton() == out:
            ToolbarBuilder._out(mw)

    @staticmethod
    def _out(mw):
        from steam_library_manager.config import config
        from steam_library_manager.core.token_store import TokenStore

        mw.session = None
        mw.access_token = None
        mw.refresh_token = None
        mw.steam_username = None

        ts = TokenStore()
        ts.clear_tokens()

        config.STEAM_USER_ID = None
        config.STEAM_ACCESS_TOKEN = None
        config.save()

        mw.user_label.setText("")
        mw.refresh_toolbar()
        mw.set_status(t("steam.login.logged_out"))
        UIHelper.show_success(mw, t("steam.login.logged_out"), "Steam")
