#
# steam_library_manager/ui/widgets/base_dialog.py
# Base dialog with buttons
#
# Copyright 2025 SwitchBros
# MIT License
#

from __future__ import annotations

from PyQt6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
)

from steam_library_manager.ui.utils.font_helper import FontHelper
from steam_library_manager.utils.i18n import t

__all__ = ["BaseDialog"]


class BaseDialog(QDialog):
    """Standard dialog base - subclasses override _build_content().

    Handles window title, optional header label, and button row.
    Most dialogs use buttons="custom" and add their own buttons.
    """

    def __init__(
        self, parent=None, title_key="", title_text="", min_width=500, show_title_label=True, buttons="ok_cancel"
    ):
        super().__init__(parent)
        title = title_text or (title_key and t(title_key) or "")
        if title:
            self.setWindowTitle("%s" % title)
        self.setMinimumWidth(min_width)
        self.setModal(True)

        self._lyt = QVBoxLayout(self)
        self._lyt.setSpacing(12)

        if show_title_label and title:
            lbl = QLabel("%s" % title)
            lbl.setFont(FontHelper.get_font(14, FontHelper.BOLD))
            self._lyt.addWidget(lbl)

        self._build_content(self._lyt)
        self._add_btns(buttons)

    def _build_content(self, layout):
        # override me
        pass

    def _add_btns(self, m):
        if m in ("none", "custom"):
            return

        r = QHBoxLayout()
        r.addStretch()

        if m == "ok_cancel":
            self._btn_can = QPushButton(t("common.cancel"))
            self._btn_can.clicked.connect(self.reject)
            r.addWidget(self._btn_can)

            self._btn_ok = QPushButton(t("common.ok"))
            self._btn_ok.clicked.connect(self.accept)
            self._btn_ok.setDefault(True)
            r.addWidget(self._btn_ok)

        elif m == "close":
            b = QPushButton(t("common.close"))
            b.clicked.connect(self.reject)
            r.addWidget(b)

        self._lyt.addLayout(r)
