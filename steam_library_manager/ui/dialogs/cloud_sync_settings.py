#
# steam_library_manager/ui/dialogs/cloud_sync_settings.py
# Cloud Sync settings tab for the settings dialog
#
# Copyright (c) 2025-2026 SwitchBros
# Licensed under the MIT License. See LICENSE for details.
#
# TODO: wire connect/disconnect to actual provider auth

from __future__ import annotations

from PyQt6.QtWidgets import (
    QButtonGroup,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QPushButton,
    QRadioButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from steam_library_manager.core.logging import logger
from steam_library_manager.utils.i18n import t

__all__ = ["CloudSyncSettingsTab"]


class CloudSyncSettingsTab(QWidget):
    # settings tab widget for cloud sync configuration

    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()

    def _build_ui(self):
        lyt = QVBoxLayout(self)

        # --- provider selection ---
        grp_prov = QGroupBox(t("cloud_sync.provider_label"))
        prov_lyt = QVBoxLayout(grp_prov)

        self.provider_group = QButtonGroup(self)
        self.radio_none = QRadioButton(t("cloud_sync.provider_none"))
        self.radio_webdav = QRadioButton(t("cloud_sync.provider_webdav"))
        self.radio_rclone = QRadioButton("rclone (MEGA, Google Drive, Dropbox, ...)")

        self.provider_group.addButton(self.radio_none, 0)
        self.provider_group.addButton(self.radio_webdav, 1)
        self.provider_group.addButton(self.radio_rclone, 2)

        self.radio_none.setChecked(True)

        prov_lyt.addWidget(self.radio_none)
        prov_lyt.addWidget(self.radio_webdav)
        prov_lyt.addWidget(self.radio_rclone)

        lyt.addWidget(grp_prov)

        # --- provider credentials (stacked) ---
        self.cred_stack = QStackedWidget()

        # page 0: no provider - empty placeholder
        empty_page = QWidget()
        self.cred_stack.addWidget(empty_page)

        # page 1: WebDAV credentials
        webdav_page = QWidget()
        wdav_lyt = QFormLayout(webdav_page)
        self.webdav_url = QLineEdit()
        self.webdav_url.setPlaceholderText(t("cloud_sync.webdav_url_hint"))
        self.webdav_user = QLineEdit()
        self.webdav_pass = QLineEdit()
        self.webdav_pass.setEchoMode(QLineEdit.EchoMode.Password)
        wdav_lyt.addRow(t("cloud_sync.webdav_url_label"), self.webdav_url)
        wdav_lyt.addRow(t("cloud_sync.webdav_user_label"), self.webdav_user)
        wdav_lyt.addRow(t("cloud_sync.webdav_pass_label"), self.webdav_pass)
        self.cred_stack.addWidget(webdav_page)

        # page 2: rclone remote selection
        rclone_page = QWidget()
        rc_lyt = QVBoxLayout(rclone_page)

        # scrollable list of configured remotes
        rc_lyt.addWidget(QLabel(t("cloud_sync.rclone_remote_label") + ":"))
        self.rclone_list = QListWidget()
        self.rclone_list.setMaximumHeight(120)
        self._refresh_rclone_remotes()
        rc_lyt.addWidget(self.rclone_list)

        # hidden line edit to store selected remote (for get_settings compat)
        self.rclone_remote = QLineEdit()
        self.rclone_remote.setVisible(False)
        rc_lyt.addWidget(self.rclone_remote)

        # sync selection to line edit
        self.rclone_list.currentTextChanged.connect(self.rclone_remote.setText)

        # setup wizard button
        self.btn_rclone_setup = QPushButton(t("cloud_sync.rclone_setup_wizard_btn"))
        self.btn_rclone_setup.clicked.connect(self._open_rclone_setup)
        rc_lyt.addWidget(self.btn_rclone_setup)

        self.cred_stack.addWidget(rclone_page)

        # switch stack page when provider changes
        self.provider_group.idToggled.connect(self._on_provider_changed)
        lyt.addWidget(self.cred_stack)

        # --- sync mode ---
        grp_mode = QGroupBox(t("cloud_sync.sync_mode_label"))
        mode_lyt = QVBoxLayout(grp_mode)

        self.mode_group = QButtonGroup(self)
        self.mode_manual = QRadioButton(t("cloud_sync.mode_manual"))
        self.mode_auto_upload = QRadioButton(t("cloud_sync.mode_auto_upload"))
        self.mode_full_auto = QRadioButton(t("cloud_sync.mode_full_auto"))

        self.mode_group.addButton(self.mode_manual, 0)
        self.mode_group.addButton(self.mode_auto_upload, 1)
        self.mode_group.addButton(self.mode_full_auto, 2)

        self.mode_manual.setChecked(True)

        mode_lyt.addWidget(self.mode_manual)
        mode_lyt.addWidget(self.mode_auto_upload)
        mode_lyt.addWidget(self.mode_full_auto)

        lyt.addWidget(grp_mode)

        # --- status section ---
        grp_status = QGroupBox()
        status_lyt = QHBoxLayout(grp_status)

        self.lbl_last_sync = QLabel(t("cloud_sync.last_sync_never"))
        status_lyt.addWidget(self.lbl_last_sync)

        status_lyt.addStretch()

        self.btn_connect = QPushButton(t("cloud_sync.connect_btn"))
        self.btn_connect.clicked.connect(self._on_connect)
        status_lyt.addWidget(self.btn_connect)

        self._connected = False
        lyt.addWidget(grp_status)
        lyt.addStretch()

    def _on_provider_changed(self, btn_id: int, checked: bool):
        if checked:
            self.cred_stack.setCurrentIndex(btn_id)
            if btn_id == 2:
                self._refresh_rclone_remotes()

    def _refresh_rclone_remotes(self):
        # populate the remote list from rclone config
        self.rclone_list.clear()
        try:
            from steam_library_manager.services.cloud_sync.rclone import RcloneProvider

            remotes = RcloneProvider.list_remotes()
            for r in remotes:
                self.rclone_list.addItem(r)

            # pre-select current remote if set
            cur = self.rclone_remote.text()
            if cur:
                for i in range(self.rclone_list.count()):
                    if self.rclone_list.item(i).text() == cur:
                        self.rclone_list.setCurrentRow(i)
                        break
        except Exception:
            pass

    def _open_rclone_setup(self):
        from steam_library_manager.ui.dialogs.rclone_setup_dialog import RcloneSetupDialog

        dlg = RcloneSetupDialog(self)
        dlg.exec()

        # if a remote was created, fill it in
        if dlg.created_remote:
            self.rclone_remote.setText(dlg.created_remote)
            self._refresh_rclone_remotes()

    def _on_connect(self):
        # try to connect with current credentials
        settings = self.get_settings()
        prov = settings["provider"]

        if prov == "none":
            self.lbl_last_sync.setText(t("cloud_sync.no_provider"))
            return

        self.btn_connect.setEnabled(False)
        self.btn_connect.setText("...")

        try:
            provider = None
            if prov == "webdav":
                from steam_library_manager.services.cloud_sync.webdav import WebDAVProvider

                provider = WebDAVProvider(
                    url=settings["webdav_url"],
                    username=settings["webdav_user"],
                    password=settings["webdav_pass"],
                )
            elif prov == "rclone":
                from steam_library_manager.services.cloud_sync.rclone import RcloneProvider

                provider = RcloneProvider(remote=settings["rclone_remote"])

            if provider and provider.connect():
                self._connected = True
                provider.disconnect()
                self.btn_connect.setText(t("cloud_sync.disconnect_btn"))
                self.lbl_last_sync.setText(t("cloud_sync.status_connected"))
                logger.info("Cloud provider %s connected OK" % prov)

                # save credentials to token store (webdav only, rclone has no creds)
                if prov == "webdav":
                    from steam_library_manager.core.token_store import TokenStore

                    ts = TokenStore()
                    ts.save_cloud_credentials(
                        "webdav",
                        {
                            "url": settings["webdav_url"],
                            "username": settings["webdav_user"],
                            "password": settings["webdav_pass"],
                        },
                    )
            else:
                self._connected = False
                self.btn_connect.setText(t("cloud_sync.connect_btn"))
                self.lbl_last_sync.setText(t("cloud_sync.upload_failed", error="connection failed"))
                logger.error("Cloud provider %s connection failed" % prov)
        except Exception as exc:
            self._connected = False
            self.btn_connect.setText(t("cloud_sync.connect_btn"))
            self.lbl_last_sync.setText(t("cloud_sync.upload_failed", error=str(exc)))
            logger.error("Cloud connect error: %s" % exc)
        finally:
            self.btn_connect.setEnabled(True)

    # -- public API --

    def get_settings(self) -> dict:
        # collect current values into a dict
        prov_map = {0: "none", 1: "webdav", 2: "rclone"}
        mode_map = {0: "manual", 1: "auto_upload", 2: "full_auto"}

        prov_id = self.provider_group.checkedId()
        mode_id = self.mode_group.checkedId()

        return {
            "provider": prov_map.get(prov_id, "none"),
            "sync_mode": mode_map.get(mode_id, "manual"),
            "webdav_url": self.webdav_url.text().strip(),
            "webdav_user": self.webdav_user.text().strip(),
            "webdav_pass": self.webdav_pass.text(),
            "rclone_remote": self.rclone_remote.text().strip(),
        }

    def load_settings(self, cfg):
        # populate from a config-like object
        prov = getattr(cfg, "CLOUD_PROVIDER", "none")
        prov_ids = {"none": 0, "webdav": 1, "rclone": 2}
        btn = self.provider_group.button(prov_ids.get(prov, 0))
        if btn:
            btn.setChecked(True)

        mode = getattr(cfg, "CLOUD_SYNC_MODE", "manual")
        mode_ids = {"manual": 0, "auto_upload": 1, "full_auto": 2}
        mbtn = self.mode_group.button(mode_ids.get(mode, 0))
        if mbtn:
            mbtn.setChecked(True)

        self.webdav_url.setText(getattr(cfg, "CLOUD_WEBDAV_URL", ""))
        self.rclone_remote.setText(getattr(cfg, "CLOUD_RCLONE_REMOTE", ""))

        # load webdav credentials from token store
        try:
            if prov == "webdav":
                from steam_library_manager.core.token_store import TokenStore

                ts = TokenStore()
                creds = ts.load_cloud_credentials("webdav") or {}
                self.webdav_user.setText(creds.get("username", ""))
                self.webdav_pass.setText(creds.get("password", ""))
                if creds:
                    self._connected = True
                    self.btn_connect.setText(t("cloud_sync.disconnect_btn"))
                    self.lbl_last_sync.setText(t("cloud_sync.status_connected"))
            elif prov == "rclone" and getattr(cfg, "CLOUD_RCLONE_REMOTE", ""):
                self._connected = True
                self.btn_connect.setText(t("cloud_sync.disconnect_btn"))
                self.lbl_last_sync.setText(t("cloud_sync.status_connected"))
        except Exception:
            pass

        last = getattr(cfg, "CLOUD_LAST_SYNC", None)
        if last:
            self.lbl_last_sync.setText(t("cloud_sync.last_sync", time=str(last)))
        elif not self._connected:
            self.lbl_last_sync.setText(t("cloud_sync.last_sync_never"))
