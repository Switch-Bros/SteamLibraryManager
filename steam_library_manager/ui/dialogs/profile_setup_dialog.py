#
# steam_library_manager/ui/dialogs/profile_setup_dialog.py
# First-run profile setup wizard dialog
#
# Copyright (c) 2025-2026 SwitchBros
# Licensed under the MIT License. See LICENSE for details.
#

from PyQt6.QtCore import QThread, pyqtSignal
from PyQt6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QRadioButton,
    QComboBox,
    QPushButton,
    QLabel,
    QLineEdit,
    QProgressBar,
)
from steam_library_manager.core.steam_account_scanner import scan_steam_accounts, fetch_steam_display_name
from steam_library_manager.ui.widgets.base_dialog import BaseDialog
from steam_library_manager.ui.widgets.ui_helper import UIHelper
from steam_library_manager.utils.i18n import t
from steam_library_manager.utils.timeouts import HTTP_TIMEOUT

__all__ = ["AccountScanWorker", "ProfileSetupDialog"]


class AccountScanWorker(QThread):
    """Background worker that scans local Steam accounts
    without blocking the UI thread."""

    accounts_found = pyqtSignal(list)
    scan_complete = pyqtSignal()

    def __init__(self, steam_path):
        super().__init__()
        self.steam_path = steam_path

    def run(self):
        # scan accounts in background thread
        accounts = scan_steam_accounts(self.steam_path)
        self.accounts_found.emit(accounts)
        self.scan_complete.emit()


class ProfileSetupDialog(BaseDialog):
    """Profile setup dialog for selecting or configuring a Steam user.
    Supports dropdown, Steam login, manual SteamID64, and community URL."""

    def __init__(self, steam_path, parent=None):
        self.steam_path = steam_path
        self.selected_steam_id_64 = None
        self.selected_display_name = None
        self.scanned_accounts = []

        super().__init__(
            parent,
            title_key="steam.profile_setup.title",
            min_width=500,
            show_title_label=False,
            buttons="custom",
        )
        self._start_scan()

    def _build_content(self, layout):
        # builds the profile setup form with account options
        layout.setSpacing(15)

        # header
        hdr = QLabel(t("steam.profile_setup.header"))
        hdr.setWordWrap(True)
        hdr.setStyleSheet("font-size: 14px; font-weight: bold;")
        layout.addWidget(hdr)

        # option 1: select from dropdown
        self.radio_select = QRadioButton(t("steam.profile_setup.select_from_list"))
        self.radio_select.setChecked(True)
        layout.addWidget(self.radio_select)

        self.combo_accounts = QComboBox()
        self.combo_accounts.setEnabled(False)
        layout.addWidget(self.combo_accounts)

        # progress bar for scanning
        self.scan_progress = QProgressBar()
        self.scan_progress.setRange(0, 0)
        self.scan_progress.setTextVisible(True)
        self.scan_progress.setFormat(t("steam.profile_setup.scanning"))
        layout.addWidget(self.scan_progress)

        # option 2: login with Steam
        self.radio_login = QRadioButton(t("steam.profile_setup.login_with_steam"))
        layout.addWidget(self.radio_login)

        login_row = QHBoxLayout()
        self.btn_steam_login = QPushButton(t("steam.login.button"))
        self.btn_steam_login.setEnabled(False)
        self.btn_steam_login.clicked.connect(self._on_steam_login)
        login_row.addWidget(self.btn_steam_login)
        login_row.addStretch()
        layout.addLayout(login_row)

        # option 3: enter SteamID64 manually
        self.radio_manual = QRadioButton(t("steam.profile_setup.enter_manually"))
        layout.addWidget(self.radio_manual)

        manual_row = QHBoxLayout()
        manual_row.addWidget(QLabel(t("steam.profile_setup.steamid64_label")))
        self.input_steamid = QLineEdit()
        self.input_steamid.setPlaceholderText("76561198004190954")
        self.input_steamid.setEnabled(False)
        manual_row.addWidget(self.input_steamid)
        layout.addLayout(manual_row)

        # option 4: enter Steam Community URL
        self.radio_community = QRadioButton(t("steam.profile_setup.enter_community_url"))
        layout.addWidget(self.radio_community)

        comm_row = QHBoxLayout()
        comm_row.addWidget(QLabel("steamcommunity.com/id/"))
        self.input_community = QLineEdit()
        self.input_community.setPlaceholderText(t("steam.profile_setup.community_placeholder"))
        self.input_community.setEnabled(False)
        comm_row.addWidget(self.input_community)
        layout.addLayout(comm_row)

        # buttons
        layout.addStretch()
        btn_row = QHBoxLayout()
        btn_row.addStretch()

        self.btn_cancel = QPushButton(t("common.cancel"))
        self.btn_cancel.clicked.connect(self.reject)
        btn_row.addWidget(self.btn_cancel)

        self.btn_continue = QPushButton(t("common.continue"))
        self.btn_continue.setDefault(True)
        self.btn_continue.clicked.connect(self._on_continue)
        btn_row.addWidget(self.btn_continue)

        layout.addLayout(btn_row)

        # connect radio buttons to enable/disable inputs
        self.radio_select.toggled.connect(self._toggle_inputs)
        self.radio_login.toggled.connect(self._toggle_inputs)
        self.radio_manual.toggled.connect(self._toggle_inputs)
        self.radio_community.toggled.connect(self._toggle_inputs)

    def _start_scan(self):
        # start background thread to scan Steam accounts
        self.scan_worker = AccountScanWorker(self.steam_path)
        self.scan_worker.accounts_found.connect(self._on_found)
        self.scan_worker.scan_complete.connect(self._on_done)
        self.scan_worker.start()

    def _on_found(self, accounts):
        # handle accounts found from scan
        self.scanned_accounts = accounts

        self.combo_accounts.clear()
        for acct in accounts:
            self.combo_accounts.addItem(str(acct), acct)

        if accounts:
            self.combo_accounts.setEnabled(True)
        else:
            self.combo_accounts.addItem(t("steam.profile_setup.no_accounts_found"))

    def _on_done(self):
        # handle scan completion
        self.scan_progress.hide()

        if not self.scanned_accounts:
            self.radio_login.setChecked(True)
            self.btn_steam_login.setEnabled(True)

    def _toggle_inputs(self):
        # enable/disable inputs based on selected radio button
        self.combo_accounts.setEnabled(self.radio_select.isChecked() and bool(self.scanned_accounts))
        self.btn_steam_login.setEnabled(self.radio_login.isChecked())
        self.input_steamid.setEnabled(self.radio_manual.isChecked())
        self.input_community.setEnabled(self.radio_community.isChecked())

    def _on_steam_login(self):
        # handle Steam login button click
        from steam_library_manager.ui.dialogs.steam_modern_login_dialog import ModernSteamLoginDialog

        dlg = ModernSteamLoginDialog(self)
        result = dlg.exec()

        if result == QDialog.DialogCode.Accepted:
            if dlg.steam_id_64 is not None:
                self.selected_steam_id_64 = dlg.steam_id_64
                self.selected_display_name = dlg.display_name

                self._store_tokens(dlg.login_result, str(dlg.steam_id_64))

                self.accept()
            else:
                UIHelper.show_warning(self, t("steam.login.error_no_steam_id"))

    @staticmethod
    def _store_tokens(login_result, steam_id):
        # persist access/refresh tokens from a successful login
        if not login_result:
            return

        from steam_library_manager.core.token_store import TokenStore
        from steam_library_manager.config import config

        at = login_result.get("access_token")
        rt = login_result.get("refresh_token")

        if at:
            config.STEAM_ACCESS_TOKEN = at

        if at and rt:
            store = TokenStore()
            store.save_tokens(at, rt, steam_id)

    def _on_continue(self):
        # handle Continue button click
        if self.radio_select.isChecked():
            idx = self.combo_accounts.currentIndex()
            if idx >= 0:
                acct = self.combo_accounts.itemData(idx)
                if acct:
                    self.selected_steam_id_64 = acct.steam_id_64
                    self.selected_display_name = acct.display_name
                    self.accept()
                    return

            UIHelper.show_warning(self, t("steam.profile_setup.select_account_first"))

        elif self.radio_login.isChecked():
            UIHelper.show_info(
                self,
                t("steam.profile_setup.click_steam_login_button"),
                title=t("steam.profile_setup.login_required"),
            )

        elif self.radio_manual.isChecked():
            raw = self.input_steamid.text().strip()

            if not raw:
                UIHelper.show_warning(self, t("steam.profile_setup.enter_steamid64"))
                return

            try:
                sid = int(raw)

                if sid < 76561197960265728:
                    raise ValueError

                self.selected_steam_id_64 = sid
                self.selected_display_name = fetch_steam_display_name(sid)
                self.accept()

            except ValueError:
                UIHelper.show_warning(self, t("steam.profile_setup.invalid_steamid64"))

        elif self.radio_community.isChecked():
            slug = self.input_community.text().strip().lower()

            if not slug:
                UIHelper.show_warning(self, t("steam.profile_setup.enter_custom_url"))
                return

            sid = self._resolve_url(slug)

            if sid:
                self.selected_steam_id_64 = sid
                self.selected_display_name = fetch_steam_display_name(sid)
                self.accept()
            else:
                UIHelper.show_warning(self, t("steam.profile_setup.custom_url_not_found"))

    @staticmethod
    def _resolve_url(custom_url):
        # resolve Steam Community custom URL to SteamID64
        import requests
        import xml.etree.ElementTree as ET

        try:
            url = "https://steamcommunity.com/id/%s?xml=1" % custom_url
            resp = requests.get(url, timeout=HTTP_TIMEOUT)

            if resp.status_code == 200:
                tree = ET.fromstring(resp.content)
                elem = tree.find("steamID64")

                if elem is not None and elem.text:
                    return int(elem.text)

        except (requests.RequestException, ET.ParseError, ValueError):
            pass

        return None
