#
# steam_library_manager/ui/dialogs/pegi_selector_dialog.py
# Manual PEGI age rating assignment dialog
#
# Copyright © 2025-2026 SwitchBros
# Licensed under the MIT License. See LICENSE for details.
#

from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QPixmap, QIcon
from PyQt6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QGridLayout, QWidget

from steam_library_manager.config import config
from steam_library_manager.ui.theme import Theme
from steam_library_manager.ui.widgets.base_dialog import BaseDialog
from steam_library_manager.utils.i18n import t

__all__ = ["PEGIIconButton", "PEGISelectorDialog"]


class PEGIIconButton(QPushButton):
    # PEGI icon button
    def __init__(self, rt, ip, par=None):
        super().__init__(par)
        self.rating = rt
        self.setFixedSize(140, 140)
        self.setStyleSheet(Theme.pegi_btn())

        if ip.exists():
            px = QPixmap(str(ip))
            scaled = px.scaled(120, 120, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            self.setIcon(QIcon(scaled))
            self.setIconSize(scaled.size())
        else:
            self.setText("PEGI\n%s" % rt)


class PEGISelectorDialog(BaseDialog):
    """PEGI rating picker - shows icons in grid."""

    rating_selected = pyqtSignal(str)

    def __init__(self, cur="", par=None):
        self.cur_rating = cur
        self.sel_rating = ""
        super().__init__(
            par, title_key="ui.pegi_selector.title", min_width=500, show_title_label=False, buttons="custom"
        )

    def _build_content(self, layout):
        layout.setSpacing(20)

        ttl = QLabel(t("ui.pegi_selector.instruction"))
        ttl.setStyleSheet("font-size: 14px; font-weight: bold; color: %s;" % Theme.TXT_PRI)
        ttl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(ttl)

        # Grid with icons
        gw = QWidget()
        grid = QGridLayout(gw)
        grid.setSpacing(15)

        ages = ["3", "7", "12", "16", "18"]
        idir = config.ICONS_DIR

        row, col = 0, 0
        for r in ages:
            ip = idir / ("PEGI%s.webp" % r)
            btn = PEGIIconButton(r, ip, self)
            btn.clicked.connect(lambda _c=False, rt=r: self._pick(rt))

            if r == self.cur_rating:
                # highlight current
                btn.setStyleSheet(btn.styleSheet() + "QPushButton { border: 3px solid %s; }" % Theme.PEGI_HVR)

            grid.addWidget(btn, row, col)
            col += 1
            if col >= 3:
                col = 0
                row += 1

        layout.addWidget(gw)

        # Buttons row
        bl = QHBoxLayout()
        bl.addStretch()

        rm = QPushButton(t("ui.pegi_selector.remove"))
        # Red remove btn
        rm.setStyleSheet(
            "QPushButton { background-color: #c23030; color: white;"
            " padding: 8px 16px; border-radius: 4px; font-weight: bold; }"
            " QPushButton:hover { background-color: #d04040; }"
        )
        rm.clicked.connect(self._remove)
        bl.addWidget(rm)

        cn = QPushButton(t("common.cancel"))
        # Grey cancel
        cn.setStyleSheet(
            "QPushButton { background-color: #3d4450; color: white;"
            " padding: 8px 16px; border-radius: 4px; }"
            " QPushButton:hover { background-color: #4d5460; }"
        )
        cn.clicked.connect(self.reject)
        bl.addWidget(cn)

        layout.addLayout(bl)

    def _pick(self, r):
        self.sel_rating = r
        self.rating_selected.emit(r)
        self.accept()

    def _remove(self):
        self.sel_rating = ""
        self.rating_selected.emit("")
        self.accept()

    def get_selected_rating(self):
        return self.sel_rating
