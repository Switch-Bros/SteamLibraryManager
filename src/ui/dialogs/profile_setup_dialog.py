"""
Profile Setup Dialog.

This dialog is shown on first launch to let the user select their Steam account.
Provides 4 options:
1. Select from dropdown (scanned local accounts)
2. Login with Steam (QR Code / Password)
3. Enter SteamID64 manually
4. Enter Steam Community URL
"""
from __future__ import annotations

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QRadioButton, QComboBox,
    QPushButton, QLabel, QLineEdit, QMessageBox, QProgressBar
)
from PyQt6.QtCore import QThread, pyqtSignal

from src.core.steam_account import SteamAccount
from src.core.steam_account_scanner import scan_steam_accounts, fetch_steam_display_name
from src.utils.i18n import t

class AccountScanWorker(QThread):
    """Background worker to scan Steam accounts without blocking UI."""

    accounts_found = pyqtSignal(list)
    scan_complete = pyqtSignal()

    def __init__(self, steam_path: str):
        super().__init__()
        self.steam_path = steam_path

    def run(self):
        """Scan accounts in background thread."""
        accounts = scan_steam_accounts(self.steam_path)
        self.accounts_found.emit(accounts)
        self.scan_complete.emit()

class ProfileSetupDialog(QDialog):
    """Profile setup dialog for selecting/configuring Steam user.

    Provides 4 methods to select a Steam account:
    - Select from dropdown of local Steam accounts
    - Login with Steam (QR/Password)
    - Enter SteamID64 manually
    - Enter Steam Community custom URL

    Attributes:
        steam_path: Path to Steam installation
        selected_steam_id_64: The SteamID64 chosen by the user
        selected_display_name: The display name of the selected account
        scanned_accounts: List of accounts found in userdata/
    """

    def __init__(self, steam_path: str, parent=None):
        """Initialize the profile setup dialog.

        Args:
            steam_path: Path to the Steam installation directory
            parent: Parent widget
        """
        super().__init__(parent)

        self.steam_path = steam_path
        self.selected_steam_id_64: int | None = None
        self.selected_display_name: str | None = None
        self.scanned_accounts: list[SteamAccount] = []

        self._setup_ui()
        self._start_account_scan()

    def _setup_ui(self):
        """Setup the UI layout."""
        self.setWindowTitle(t('ui.profile_setup.title'))
        self.setMinimumWidth(500)

        layout = QVBoxLayout(self)
        layout.setSpacing(15)

        # Header
        header = QLabel(t('ui.profile_setup.header'))
        header.setWordWrap(True)
        header.setStyleSheet("font-size: 14px; font-weight: bold;")
        layout.addWidget(header)

        # Option 1: Select from dropdown
        self.radio_select = QRadioButton(t('ui.profile_setup.select_from_list'))
        self.radio_select.setChecked(True)
        layout.addWidget(self.radio_select)

        self.combo_accounts = QComboBox()
        self.combo_accounts.setEnabled(False)
        layout.addWidget(self.combo_accounts)

        # Progress bar for scanning
        self.scan_progress = QProgressBar()
        self.scan_progress.setRange(0, 0)
        self.scan_progress.setTextVisible(True)
        self.scan_progress.setFormat(t('ui.profile_setup.scanning'))
        layout.addWidget(self.scan_progress)

        # Option 2: Login with Steam
        self.radio_login = QRadioButton(t('ui.profile_setup.login_with_steam'))
        layout.addWidget(self.radio_login)

        login_layout = QHBoxLayout()
        self.btn_steam_login = QPushButton(t('ui.login.button'))
        self.btn_steam_login.setEnabled(False)
        self.btn_steam_login.clicked.connect(self._on_steam_login)
        login_layout.addWidget(self.btn_steam_login)
        login_layout.addStretch()
        layout.addLayout(login_layout)

        # Option 3: Enter SteamID64 manually
        self.radio_manual = QRadioButton(t('ui.profile_setup.enter_manually'))
        layout.addWidget(self.radio_manual)

        manual_layout = QHBoxLayout()
        manual_layout.addWidget(QLabel(t('ui.profile_setup.steamid64_label')))
        self.input_steamid = QLineEdit()
        self.input_steamid.setPlaceholderText("76561198004190954")
        self.input_steamid.setEnabled(False)
        manual_layout.addWidget(self.input_steamid)
        layout.addLayout(manual_layout)

        # Option 4: Enter Steam Community URL
        self.radio_community = QRadioButton(t('ui.profile_setup.enter_community_url'))
        layout.addWidget(self.radio_community)

        community_layout = QHBoxLayout()
        community_layout.addWidget(QLabel("steamcommunity.com/id/"))
        self.input_community = QLineEdit()
        self.input_community.setPlaceholderText(t('ui.profile_setup.community_placeholder'))
        self.input_community.setEnabled(False)
        community_layout.addWidget(self.input_community)
        layout.addLayout(community_layout)

        # Buttons
        layout.addStretch()
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        self.btn_cancel = QPushButton(t('common.cancel'))
        self.btn_cancel.clicked.connect(self.reject)
        button_layout.addWidget(self.btn_cancel)

        self.btn_continue = QPushButton(t('common.continue'))
        self.btn_continue.setDefault(True)
        self.btn_continue.clicked.connect(self._on_continue)
        button_layout.addWidget(self.btn_continue)

        layout.addLayout(button_layout)

        # Connect radio buttons to enable/disable inputs
        self.radio_select.toggled.connect(self._update_input_states)
        self.radio_login.toggled.connect(self._update_input_states)
        self.radio_manual.toggled.connect(self._update_input_states)
        self.radio_community.toggled.connect(self._update_input_states)

    def _start_account_scan(self):
        """Start background thread to scan Steam accounts."""
        self.scan_worker = AccountScanWorker(self.steam_path)
        self.scan_worker.accounts_found.connect(self._on_accounts_found)
        self.scan_worker.scan_complete.connect(self._on_scan_complete)
        self.scan_worker.start()

    def _on_accounts_found(self, accounts: list[SteamAccount]):
        """Handle accounts found from scan.

        Args:
            accounts: List of SteamAccount objects found
        """
        self.scanned_accounts = accounts

        # Populate dropdown
        self.combo_accounts.clear()
        for account in accounts:
            self.combo_accounts.addItem(str(account), account)

        if accounts:
            self.combo_accounts.setEnabled(True)
        else:
            self.combo_accounts.addItem(t('ui.profile_setup.no_accounts_found'))

    def _on_scan_complete(self):
        """Handle scan completion."""
        self.scan_progress.hide()

        if not self.scanned_accounts:
            self.radio_login.setChecked(True)
            self.btn_steam_login.setEnabled(True)

    def _update_input_states(self):
        """Enable/disable inputs based on selected radio button."""
        self.combo_accounts.setEnabled(self.radio_select.isChecked() and bool(self.scanned_accounts))
        self.btn_steam_login.setEnabled(self.radio_login.isChecked())
        self.input_steamid.setEnabled(self.radio_manual.isChecked())
        self.input_community.setEnabled(self.radio_community.isChecked())

    def _on_steam_login(self):
        """Handle Steam login button click."""
        from src.ui.dialogs.steam_modern_login_dialog import ModernSteamLoginDialog

        dialog = ModernSteamLoginDialog(self)
        result = dialog.exec()

        if result == QDialog.DialogCode.Accepted:
            # Get steam_id_64 directly (already int!)
            if dialog.steam_id_64 is not None:
                self.selected_steam_id_64 = dialog.steam_id_64
                self.selected_display_name = dialog.display_name
                self.accept()
            else:
                QMessageBox.warning(
                    self,
                    t('common.error'),
                    t('ui.login.error_no_steam_id')
                )

    def _on_continue(self):
        """Handle Continue button click."""
        if self.radio_select.isChecked():
            current_index = self.combo_accounts.currentIndex()
            if current_index >= 0:
                account = self.combo_accounts.itemData(current_index)
                if account:
                    self.selected_steam_id_64 = account.steam_id_64
                    self.selected_display_name = account.display_name
                    self.accept()
                    return

            QMessageBox.warning(self, t('common.error'), t('ui.profile_setup.select_account_first'))

        elif self.radio_login.isChecked():
            QMessageBox.information(
                self,
                t('ui.profile_setup.login_required'),
                t('ui.profile_setup.click_steam_login_button')
            )

        elif self.radio_manual.isChecked():
            steamid_text = self.input_steamid.text().strip()

            if not steamid_text:
                QMessageBox.warning(self, t('common.error'), t('ui.profile_setup.enter_steamid64'))
                return

            try:
                steam_id_64 = int(steamid_text)

                if steam_id_64 < 76561197960265728:
                    raise ValueError

                self.selected_steam_id_64 = steam_id_64
                self.selected_display_name = fetch_steam_display_name(steam_id_64)
                self.accept()

            except ValueError:
                QMessageBox.warning(
                    self,
                    t('common.error'),
                    t('ui.profile_setup.invalid_steamid64')
                )

        elif self.radio_community.isChecked():
            custom_url = self.input_community.text().strip().lower()

            if not custom_url:
                QMessageBox.warning(self, t('common.error'), t('ui.profile_setup.enter_custom_url'))
                return

            steam_id_64 = self._resolve_custom_url(custom_url)

            if steam_id_64:
                self.selected_steam_id_64 = steam_id_64
                self.selected_display_name = fetch_steam_display_name(steam_id_64)
                self.accept()
            else:
                QMessageBox.warning(
                    self,
                    t('common.error'),
                    t('ui.profile_setup.custom_url_not_found')
                )

    @staticmethod
    def _resolve_custom_url(custom_url: str) -> int | None:
        """Resolve Steam Community custom URL to SteamID64.

        Args:
            custom_url: The custom URL part (e.g., "heikesfootslave")

        Returns:
            SteamID64 if found, None otherwise
        """
        import requests
        import xml.etree.ElementTree as ElementTree

        try:
            url = f"https://steamcommunity.com/id/{custom_url}?xml=1"
            response = requests.get(url, timeout=10)

            if response.status_code == 200:
                tree = ElementTree.fromstring(response.content)
                steam_id_element = tree.find('steamID64')

                if steam_id_element is not None and steam_id_element.text:
                    return int(steam_id_element.text)

        except (requests.RequestException, ElementTree.ParseError, ValueError):
            pass

        return None