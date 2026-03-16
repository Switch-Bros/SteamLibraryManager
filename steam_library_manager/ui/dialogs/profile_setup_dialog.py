#
# steam_library_manager/ui/dialogs/profile_setup_dialog.py
# First-launch dialog for Steam account selection
#
# Copyright (c) 2025-2026 SwitchBros
# Licensed under the MIT License. See LICENSE for details.
#

from __future__ import annotations

from PyQt6.QtCore import QThread, pyqtSignal
from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QRadioButton,
    QComboBox,
    QPushButton,
    QLabel,
    QLineEdit,
    QProgressBar,
)

from steam_library_manager.core.steam_account import SteamAccount
from steam_library_manager.core.steam_account_scanner import scan_steam_accounts, fetch_steam_display_name
from steam_library_manager.ui.widgets.base_dialog import BaseDialog
from steam_library_manager.ui.widgets.ui_helper import UIHelper
from steam_library_manager.utils.i18n import t
from steam_library_manager.utils.timeouts import HTTP_TIMEOUT

__all__ = ["AccountScanWorker", "ProfileSetupDialog"]


class AccountScanWorker(QThread):
    """Scan Steam accounts in a background thread."""

    accounts_found = pyqtSignal(list)
    scan_complete = pyqtSignal()

    def __init__(self, steam_path: str):
        super().__init__()
        self.steam_path = steam_path

    def run(self):
        accounts = scan_steam_accounts(self.steam_path)
        self.accounts_found.emit(accounts)
        self.scan_complete.emit()


class ProfileSetupDialog(BaseDialog):
    """Steam account selection - dropdown, QR login, manual ID, or community URL."""

    def __init__(self, steam_path: str, parent=None):
        self.steam_path = steam_path
        self.selected_steam_id_64: int | None = None
        self.selected_display_name: str | None = None
        self.scanned_accounts: list[SteamAccount] = []

        super().__init__(
            parent,
            title_key="steam.profile_setup.title",
            min_width=500,
            show_title_label=False,
            buttons="custom",
        )
        self._start_account_scan()

    def _build_content(self, layout: QVBoxLayout) -> None:
        layout.setSpacing(15)

        # Header
        header = QLabel(t("steam.profile_setup.header"))
        header.setWordWrap(True)
        header.setStyleSheet("font-size: 14px; font-weight: bold;")
        layout.addWidget(header)

        # Select from dropdown
        self.radio_select = QRadioButton(t("steam.profile_setup.select_from_list"))
        self.radio_select.setChecked(True)
        layout.addWidget(self.radio_select)

        self.combo_accounts = QComboBox()
        self.combo_accounts.setEnabled(False)
        layout.addWidget(self.combo_accounts)

        # Progress bar for scanning
        self.scan_progress = QProgressBar()
        self.scan_progress.setRange(0, 0)
        self.scan_progress.setTextVisible(True)
        self.scan_progress.setFormat(t("steam.profile_setup.scanning"))
        layout.addWidget(self.scan_progress)

        # Login with Steam
        self.radio_login = QRadioButton(t("steam.profile_setup.login_with_steam"))
        layout.addWidget(self.radio_login)

        login_layout = QHBoxLayout()
        self.btn_steam_login = QPushButton(t("steam.login.button"))
        self.btn_steam_login.setEnabled(False)
        self.btn_steam_login.clicked.connect(self._on_steam_login)
        login_layout.addWidget(self.btn_steam_login)
        login_layout.addStretch()
        layout.addLayout(login_layout)

        # Manual SteamID64
        self.radio_manual = QRadioButton(t("steam.profile_setup.enter_manually"))
        layout.addWidget(self.radio_manual)

        manual_layout = QHBoxLayout()
        manual_layout.addWidget(QLabel(t("steam.profile_setup.steamid64_label")))
        self.input_steamid = QLineEdit()
        self.input_steamid.setPlaceholderText("76561198004190954")
        self.input_steamid.setEnabled(False)
        manual_layout.addWidget(self.input_steamid)
        layout.addLayout(manual_layout)

        # Community URL
        self.radio_community = QRadioButton(t("steam.profile_setup.enter_community_url"))
        layout.addWidget(self.radio_community)

        community_layout = QHBoxLayout()
        community_layout.addWidget(QLabel("steamcommunity.com/id/"))
        self.input_community = QLineEdit()
        self.input_community.setPlaceholderText(t("steam.profile_setup.community_placeholder"))
        self.input_community.setEnabled(False)
        community_layout.addWidget(self.input_community)
        layout.addLayout(community_layout)

        # Buttons
        layout.addStretch()
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        self.btn_cancel = QPushButton(t("common.cancel"))
        self.btn_cancel.clicked.connect(self.reject)
        button_layout.addWidget(self.btn_cancel)

        self.btn_continue = QPushButton(t("common.continue"))
        self.btn_continue.setDefault(True)
        self.btn_continue.clicked.connect(self._on_continue)
        button_layout.addWidget(self.btn_continue)

        layout.addLayout(button_layout)

        self.radio_select.toggled.connect(self._update_input_states)
        self.radio_login.toggled.connect(self._update_input_states)
        self.radio_manual.toggled.connect(self._update_input_states)
        self.radio_community.toggled.connect(self._update_input_states)

    def _start_account_scan(self):
        self.scan_worker = AccountScanWorker(self.steam_path)
        self.scan_worker.accounts_found.connect(self._on_accounts_found)
        self.scan_worker.scan_complete.connect(self._on_scan_complete)
        self.scan_worker.start()

    def _on_accounts_found(self, accounts: list[SteamAccount]):
        self.scanned_accounts = accounts

        self.combo_accounts.clear()
        for account in accounts:
            self.combo_accounts.addItem(str(account), account)

        if accounts:
            self.combo_accounts.setEnabled(True)
        else:
            self.combo_accounts.addItem(t("steam.profile_setup.no_accounts_found"))

    def _on_scan_complete(self):
        self.scan_progress.hide()

        if not self.scanned_accounts:
            self.radio_login.setChecked(True)
            self.btn_steam_login.setEnabled(True)

    def _update_input_states(self):
        self.combo_accounts.setEnabled(self.radio_select.isChecked() and bool(self.scanned_accounts))
        self.btn_steam_login.setEnabled(self.radio_login.isChecked())
        self.input_steamid.setEnabled(self.radio_manual.isChecked())
        self.input_community.setEnabled(self.radio_community.isChecked())

    def _on_steam_login(self):
        from steam_library_manager.ui.dialogs.steam_modern_login_dialog import ModernSteamLoginDialog

        dialog = ModernSteamLoginDialog(self)
        result = dialog.exec()

        if result == QDialog.DialogCode.Accepted:
            if dialog.steam_id_64 is not None:
                self.selected_steam_id_64 = dialog.steam_id_64
                self.selected_display_name = dialog.display_name

                self._save_login_tokens(dialog.login_result, str(dialog.steam_id_64))

                self.accept()
            else:
                UIHelper.show_warning(self, t("steam.login.error_no_steam_id"))

    @staticmethod
    def _save_login_tokens(login_result: dict | None, steam_id: str) -> None:
        if not login_result:
            return

        from steam_library_manager.core.token_store import TokenStore
        from steam_library_manager.config import config

        access_token = login_result.get("access_token")
        refresh_token = login_result.get("refresh_token")

        if access_token:
            config.STEAM_ACCESS_TOKEN = access_token

        if access_token and refresh_token:
            token_store = TokenStore()
            token_store.save_tokens(access_token, refresh_token, steam_id)

    def _on_continue(self):
        if self.radio_select.isChecked():
            current_index = self.combo_accounts.currentIndex()
            if current_index >= 0:
                account = self.combo_accounts.itemData(current_index)
                if account:
                    self.selected_steam_id_64 = account.steam_id_64
                    self.selected_display_name = account.display_name
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
            steamid_text = self.input_steamid.text().strip()

            if not steamid_text:
                UIHelper.show_warning(self, t("steam.profile_setup.enter_steamid64"))
                return

            try:
                steam_id_64 = int(steamid_text)

                if steam_id_64 < 76561197960265728:
                    raise ValueError

                self.selected_steam_id_64 = steam_id_64
                self.selected_display_name = fetch_steam_display_name(steam_id_64)
                self.accept()

            except ValueError:
                UIHelper.show_warning(self, t("steam.profile_setup.invalid_steamid64"))

        elif self.radio_community.isChecked():
            custom_url = self.input_community.text().strip().lower()

            if not custom_url:
                UIHelper.show_warning(self, t("steam.profile_setup.enter_custom_url"))
                return

            steam_id_64 = self._resolve_custom_url(custom_url)

            if steam_id_64:
                self.selected_steam_id_64 = steam_id_64
                self.selected_display_name = fetch_steam_display_name(steam_id_64)
                self.accept()
            else:
                UIHelper.show_warning(self, t("steam.profile_setup.custom_url_not_found"))

    @staticmethod
    def _resolve_custom_url(custom_url: str) -> int | None:
        import requests
        import xml.etree.ElementTree as ElementTree

        try:
            url = f"https://steamcommunity.com/id/{custom_url}?xml=1"
            response = requests.get(url, timeout=HTTP_TIMEOUT)

            if response.status_code == 200:
                tree = ElementTree.fromstring(response.content)
                steam_id_element = tree.find("steamID64")

                if steam_id_element is not None and steam_id_element.text:
                    return int(steam_id_element.text)

        except (requests.RequestException, ElementTree.ParseError, ValueError):
            pass

        return None
