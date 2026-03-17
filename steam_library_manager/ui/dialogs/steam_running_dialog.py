#
# steam_library_manager/ui/dialogs/steam_running_dialog.py
# Warning dialog when Steam is running during save
#
# Copyright 2025 SwitchBros
# MIT License
#

from __future__ import annotations

from PyQt6.QtWidgets import QVBoxLayout, QHBoxLayout, QPushButton, QLabel

from steam_library_manager.ui.theme import Theme
from steam_library_manager.ui.widgets.base_dialog import BaseDialog
from steam_library_manager.ui.widgets.ui_helper import UIHelper
from steam_library_manager.utils.i18n import t

__all__ = ["SteamRunningDialog"]


class SteamRunningDialog(BaseDialog):
    """Warns user that Steam is running and offers to kill it.

    Shows up when try to Start SLM while Steam is open and running,
    File saving would get overwritten by Steam's own cloud sync.

    Data corruption also possible if Steam is running while changing files!
    """

    CANCELLED = 0
    CLOSE_AND_SAVE = 1

    def __init__(self, p=None):
        super().__init__(
            p,
            title_key="steam.running.title",
            min_width=450,
            show_title_label=False,
            buttons="custom",
        )

    def _build_content(self, lyt):
        lyt.setSpacing(20)

        # icon + msg
        h = QHBoxLayout()

        ic = QLabel(t("emoji.warning"))
        ic.setStyleSheet("font-size: 48px;")
        h.addWidget(ic)

        m = QVBoxLayout()
        m.setSpacing(10)

        tlt = QLabel(t("steam.running.warning_title"))
        tlt.setStyleSheet("font-size: 16px; font-weight: bold;")
        m.addWidget(tlt)

        x = QLabel(t("steam.running.explanation"))
        x.setWordWrap(True)
        x.setStyleSheet("color: %s;" % Theme.TXT_MUTED)
        m.addWidget(x)

        h.addLayout(m, 1)
        lyt.addLayout(h)

        # note
        i = QLabel(t("steam.running.info"))
        i.setWordWrap(True)
        i.setStyleSheet(Theme.info_box())
        lyt.addWidget(i)

        # btns
        lyt.addStretch()
        b = QHBoxLayout()
        b.addStretch()

        self._bc = QPushButton(t("common.cancel"))
        self._bc.clicked.connect(self._cancel)
        b.addWidget(self._bc)

        self._bcs = QPushButton(t("steam.running.close_and_save"))
        self._bcs.setDefault(True)
        self._bcs.setStyleSheet(Theme.btn_danger())
        self._bcs.clicked.connect(self._kill)
        b.addWidget(self._bcs)

        lyt.addLayout(b)

    def _cancel(self):
        self.done(self.CANCELLED)

    def _kill(self):
        from steam_library_manager.core.steam_account_scanner import kill_steam_process

        if not UIHelper.confirm(self, t("steam.running.confirm_message"), title=t("steam.running.confirm_title")):
            return

        if kill_steam_process():
            UIHelper.show_success(self, t("steam.running.steam_closed"))
            self.done(self.CLOSE_AND_SAVE)
        else:
            UIHelper.show_error(self, t("steam.running.close_failed"))
