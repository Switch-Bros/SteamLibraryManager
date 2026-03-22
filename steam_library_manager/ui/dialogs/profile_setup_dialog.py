#
# steam_library_manager/ui/dialogs/profile_setup_dialog.py
# First-run profile setup wizard dialog
#
# Copyright © 2025-2026 SwitchBros
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
    # bg worker that scans local Steam accounts without blocking UI

    accounts_found = pyqtSignal(list)
    scan_complete = pyqtSignal()

    def __init__(self, path):
        super().__init__()
        self.path = path  # steam install path

    def run(self):
        # scan accounts in background
        accts = scan_steam_accounts(self.path)
        self.accounts_found.emit(accts)
        self.scan_complete.emit()


class ProfileSetupDialog(BaseDialog):
    """Profile setup dialog for selecting or configuring a Steam user.
    Supports dropdown, Steam login, manual SteamID64, and community URL.

    TODO: clean up this radio button mess, maybe use QButtonGroup?
    """

    def __init__(self, steam_path, parent=None):
        self._steam = steam_path
        self.sid = None  # selected steamid64
        self.name = None  # display name
        self._found = []  # scanned accounts

        super().__init__(
            parent,
            title_key="steam.profile_setup.title",
            min_width=500,
            show_title_label=False,
            buttons="custom",
        )
        self._scan()

    def _build_content(self, lyt):
        # build the profile setup form
        lyt.setSpacing(15)

        # header
        hdr = QLabel(t("steam.profile_setup.header"))
        hdr.setWordWrap(True)
        hdr.setStyleSheet("font-size: 14px; font-weight: bold;")
        lyt.addWidget(hdr)

        # option 1: select from dropdown
        self._rad_sel = QRadioButton(t("steam.profile_setup.select_from_list"))
        self._rad_sel.setChecked(True)
        lyt.addWidget(self._rad_sel)

        self._combo = QComboBox()
        self._combo.setEnabled(False)
        lyt.addWidget(self._combo)

        # progress bar for scanning
        self._prog = QProgressBar()
        self._prog.setRange(0, 0)
        self._prog.setTextVisible(True)
        self._prog.setFormat(t("steam.profile_setup.scanning"))
        lyt.addWidget(self._prog)

        # option 2: login with Steam
        self._rad_login = QRadioButton(t("steam.profile_setup.login_with_steam"))
        lyt.addWidget(self._rad_login)

        h = QHBoxLayout()
        self._btn_login = QPushButton(t("steam.login.button"))
        self._btn_login.setEnabled(False)
        self._btn_login.clicked.connect(self._on_steam)
        h.addWidget(self._btn_login)
        h.addStretch()
        lyt.addLayout(h)

        # option 3: enter SteamID64 manually
        self._rad_manual = QRadioButton(t("steam.profile_setup.enter_manually"))
        lyt.addWidget(self._rad_manual)

        row = QHBoxLayout()
        row.addWidget(QLabel(t("steam.profile_setup.steamid64_label")))
        self._inp_sid = QLineEdit()
        self._inp_sid.setPlaceholderText("76561198004190954")
        self._inp_sid.setEnabled(False)
        row.addWidget(self._inp_sid)
        lyt.addLayout(row)

        # option 4: enter Steam Community URL
        self._rad_url = QRadioButton(t("steam.profile_setup.enter_community_url"))
        lyt.addWidget(self._rad_url)

        r2 = QHBoxLayout()
        r2.addWidget(QLabel("steamcommunity.com/id/"))
        self._inp_url = QLineEdit()
        self._inp_url.setPlaceholderText(t("steam.profile_setup.community_placeholder"))
        self._inp_url.setEnabled(False)
        r2.addWidget(self._inp_url)
        lyt.addLayout(r2)

        # buttons
        lyt.addStretch()
        btns = QHBoxLayout()
        btns.addStretch()

        cancel = QPushButton(t("common.cancel"))
        cancel.clicked.connect(self.reject)
        btns.addWidget(cancel)

        ok = QPushButton(t("common.continue"))
        ok.setDefault(True)
        ok.clicked.connect(self._continue)
        btns.addWidget(ok)

        lyt.addLayout(btns)

        # connect radio buttons to toggle inputs
        self._rad_sel.toggled.connect(self._toggle)
        self._rad_login.toggled.connect(self._toggle)
        self._rad_manual.toggled.connect(self._toggle)
        self._rad_url.toggled.connect(self._toggle)

    def _scan(self):
        # start background scan
        self._worker = AccountScanWorker(self._steam)
        self._worker.accounts_found.connect(self._found)
        self._worker.scan_complete.connect(self._done)
        self._worker.start()

    def _found(self, accts):
        # handle accounts found from scan
        self._found = accts

        self._combo.clear()
        for a in accts:
            self._combo.addItem(str(a), a)

        if accts:
            self._combo.setEnabled(True)
        else:
            self._combo.addItem(t("steam.profile_setup.no_accounts_found"))

    def _done(self):
        # scan finished
        self._prog.hide()

        if not self._found:
            self._rad_login.setChecked(True)
            self._btn_login.setEnabled(True)

    def _toggle(self):
        # enable/disable inputs based on selection
        self._combo.setEnabled(self._rad_sel.isChecked() and bool(self._found))
        self._btn_login.setEnabled(self._rad_login.isChecked())
        self._inp_sid.setEnabled(self._rad_manual.isChecked())
        self._inp_url.setEnabled(self._rad_url.isChecked())

    def _on_steam(self):
        # Steam login button clicked
        from steam_library_manager.ui.dialogs.steam_modern_login_dialog import ModernSteamLoginDialog

        dlg = ModernSteamLoginDialog(self)
        res = dlg.exec()

        if res == QDialog.DialogCode.Accepted:
            if dlg.steam_id_64 is not None:
                self.sid = dlg.steam_id_64
                self.name = dlg.display_name

                self._store(dlg.login_result, str(dlg.steam_id_64))

                self.accept()
            else:
                UIHelper.show_warning(self, t("steam.login.error_no_steam_id"))

    @staticmethod
    def _store(result, steam_id):
        # persist tokens from successful login
        if not result:
            return

        from steam_library_manager.core.token_store import TokenStore
        from steam_library_manager.config import config

        at = result.get("access_token")
        rt = result.get("refresh_token")

        if at:
            config.STEAM_ACCESS_TOKEN = at

        if at and rt:
            store = TokenStore()
            store.save_tokens(at, rt, steam_id)

    def _continue(self):
        # handle Continue button
        if self._rad_sel.isChecked():
            i = self._combo.currentIndex()
            if i >= 0:
                a = self._combo.itemData(i)
                if a:
                    self.sid = a.steam_id_64
                    self.name = a.display_name
                    self.accept()
                    return

            UIHelper.show_warning(self, t("steam.profile_setup.select_account_first"))

        elif self._rad_login.isChecked():
            UIHelper.show_info(
                self,
                t("steam.profile_setup.click_steam_login_button"),
                title=t("steam.profile_setup.login_required"),
            )

        elif self._rad_manual.isChecked():
            raw = self._inp_sid.text().strip()

            if not raw:
                UIHelper.show_warning(self, t("steam.profile_setup.enter_steamid64"))
                return

            try:
                val = int(raw)

                if val < 76561197960265728:
                    raise ValueError

                self.sid = val
                self.name = fetch_steam_display_name(val)
                self.accept()

            except ValueError:
                UIHelper.show_warning(self, t("steam.profile_setup.invalid_steamid64"))

        elif self._rad_url.isChecked():
            slug = self._inp_url.text().strip().lower()

            if not slug:
                UIHelper.show_warning(self, t("steam.profile_setup.enter_custom_url"))
                return

            resolved = self._resolve(slug)

            if resolved:
                self.sid = resolved
                self.name = fetch_steam_display_name(resolved)
                self.accept()
            else:
                UIHelper.show_warning(self, t("steam.profile_setup.custom_url_not_found"))

    @staticmethod
    def _resolve(custom_url):
        # resolve Steam Community URL to SteamID64
        import requests
        import xml.etree.ElementTree as ET

        try:
            url = "https://steamcommunity.com/id/%s?xml=1" % custom_url
            r = requests.get(url, timeout=HTTP_TIMEOUT)

            if r.status_code == 200:
                tree = ET.fromstring(r.content)
                elem = tree.find("steamID64")

                if elem is not None and elem.text:
                    return int(elem.text)

        except (requests.RequestException, ET.ParseError, ValueError):
            pass

        return None
