#
# steam_library_manager/ui/dialogs/missing_metadata_dialog.py
# Dialog for games with incomplete metadata
#
# Copyright © 2025-2026 SwitchBros
# Licensed under the MIT License. See LICENSE for details.
#

from __future__ import annotations

import csv
from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QTableWidget,
    QTableWidgetItem,
    QPushButton,
    QLabel,
    QFileDialog,
    QHeaderView,
)

from steam_library_manager.ui.theme import Theme
from steam_library_manager.ui.utils.font_helper import FontHelper
from steam_library_manager.ui.widgets.base_dialog import BaseDialog
from steam_library_manager.ui.widgets.ui_helper import UIHelper
from steam_library_manager.utils.date_utils import format_timestamp_to_date
from steam_library_manager.utils.i18n import t

__all__ = ["MissingMetadataDialog"]


class MissingMetadataDialog(BaseDialog):
    """Shows games missing dev/pub/date."""

    def __init__(self, parent, games):
        self.games = games

        super().__init__(
            parent,
            title_key="ui.tools.missing_metadata.title",
            min_width=900,
            show_title_label=False,
            buttons="custom",
        )
        self.setMinimumHeight(600)
        self._fill()

    @staticmethod
    def _bad(val):
        # check if empty
        if val is None:
            return True
        s = str(val).strip()
        if not s:
            return True
        if s.lower() in ["unknown", "unbekannt", "none", "n/a"]:
            return True
        return False

    def _build_content(self, layout):
        # header
        h = QLabel(t("ui.tools.missing_metadata.header", count=len(self.games)))
        h.setFont(FontHelper.get_font(14, FontHelper.BOLD))
        layout.addWidget(h)

        i = QLabel(t("ui.tools.missing_metadata.info"))
        i.setWordWrap(True)
        i.setStyleSheet("color: %s; padding: 10px 0;" % Theme.TXT_MUTED)
        layout.addWidget(i)

        # table
        self.t = QTableWidget()
        self.t.setColumnCount(5)
        self.t.setHorizontalHeaderLabels(
            [
                t("ui.tools.missing_metadata.col_appid"),
                t("ui.tools.missing_metadata.col_name"),
                t("ui.tools.missing_metadata.col_developer"),
                t("ui.tools.missing_metadata.col_publisher"),
                t("ui.tools.missing_metadata.col_release"),
            ]
        )

        hh = self.t.horizontalHeader()
        hh.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        hh.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        hh.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        hh.setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        hh.setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)

        self.t.setColumnWidth(0, 70)
        self.t.setColumnWidth(2, 180)
        self.t.setColumnWidth(3, 130)
        self.t.setColumnWidth(4, 110)

        self.t.setAlternatingRowColors(True)
        layout.addWidget(self.t)

        # stats
        self.s = QLabel()
        self.s.setStyleSheet("color: %s; font-size: 10px;" % Theme.TXT_MUTED)

        st = QHBoxLayout()
        st.addWidget(self.s)
        st.addStretch()
        layout.addLayout(st)

        # buttons
        bt = QHBoxLayout()
        bt.addStretch()

        ex = QPushButton(t("ui.tools.missing_metadata.export_csv"))
        ex.clicked.connect(self._export)
        bt.addWidget(ex)

        cl = QPushButton(t("common.close"))
        cl.setDefault(True)
        cl.clicked.connect(self.accept)
        bt.addWidget(cl)

        layout.addLayout(bt)

    @staticmethod
    def _item(txt):
        # read-only item
        it = QTableWidgetItem(str(txt))
        flags = Qt.ItemFlag.ItemIsEnabled.value | Qt.ItemFlag.ItemIsSelectable.value
        it.setFlags(Qt.ItemFlag(flags))
        return it

    def _fill(self):
        # populate rows
        self.t.setRowCount(len(self.games))

        for r, g in enumerate(self.games):
            self.t.setItem(r, 0, self._item(str(g.app_id)))
            self.t.setItem(r, 1, self._item(g.name))

            # dev
            d = g.developer if g.developer else ""
            if self._bad(d):
                d = "%s %s" % (t("emoji.error"), t("ui.tools.missing_metadata.missing_marked"))
            self.t.setItem(r, 2, self._item(d))

            # pub
            p = g.publisher if g.publisher else ""
            if self._bad(p):
                p = "%s %s" % (t("emoji.error"), t("ui.tools.missing_metadata.missing_marked"))
            self.t.setItem(r, 3, self._item(p))

            # date
            rel = g.release_year if g.release_year else ""
            if self._bad(rel):
                rel = "%s %s" % (t("emoji.error"), t("ui.tools.missing_metadata.missing_marked"))
            else:
                rel = format_timestamp_to_date(rel)
            self.t.setItem(r, 4, self._item(rel))

        self.s.setText(t("ui.tools.missing_metadata.stats", count=len(self.games)))

    def _export(self):
        # export CSV
        default = "missing_metadata_%d_games.csv" % len(self.games)

        fp, _ = QFileDialog.getSaveFileName(
            self,
            t("ui.tools.missing_metadata.save_csv"),
            str(Path.home() / default),
            "CSV Files (*.csv)",
        )

        if not fp:
            return

        try:
            with open(fp, "w", newline="", encoding="utf-8") as f:
                w = csv.writer(f)

                w.writerow(
                    [
                        t("ui.tools.missing_metadata.col_appid"),
                        t("ui.tools.missing_metadata.col_name"),
                        t("ui.tools.missing_metadata.col_developer"),
                        t("ui.tools.missing_metadata.col_publisher"),
                        t("ui.tools.missing_metadata.col_release"),
                        t("ui.tools.missing_metadata.col_missing_fields"),
                    ]
                )

                for g in self.games:
                    miss = []

                    d = g.developer if g.developer else ""
                    if self._bad(d):
                        d = t("ui.tools.missing_metadata.missing")
                        miss.append(t("ui.game_details.developer"))

                    p = g.publisher if g.publisher else ""
                    if self._bad(p):
                        p = t("ui.tools.missing_metadata.missing")
                        miss.append(t("ui.game_details.publisher"))

                    rel = g.release_year if g.release_year else ""
                    if self._bad(rel):
                        rel = t("ui.tools.missing_metadata.missing")
                        miss.append(t("ui.game_details.release_year"))
                    else:
                        rel = format_timestamp_to_date(rel)

                    w.writerow([g.app_id, g.name, str(d), str(p), str(rel), ", ".join(miss)])

            UIHelper.show_success(
                self,
                t("ui.tools.missing_metadata.export_success", count=len(self.games), path=fp),
            )

        except OSError as e:
            UIHelper.show_error(self, t("ui.tools.missing_metadata.export_error", error=str(e)))
