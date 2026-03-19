#
# steam_library_manager/ui/dialogs/health_check_dialog.py
# Dialog displaying library health check results
#
# Copyright © 2025-2026 SwitchBros
# Licensed under the MIT License. See LICENSE for details.
#

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QHeaderView,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from steam_library_manager.ui.widgets.base_dialog import BaseDialog
from steam_library_manager.utils.i18n import t

__all__ = ["HealthCheckResultDialog"]

# Status emoji mapping
# status -> emoji key (resolved at runtime via t())
_STATUS_EMOJI_KEYS = {
    "available": "emoji.green_circle",
    "age_gate": "emoji.yellow_circle",
    "geo_locked": "emoji.yellow_circle",
    "delisted": "emoji.red_circle",
    "removed": "emoji.red_circle",
    "unknown": "emoji.white_circle",
}


class HealthCheckResultDialog(BaseDialog):
    """Shows library health check results in three tabs:
    store availability, missing data, and cache freshness.
    """

    def __init__(self, parent, report):
        self._report = report
        super().__init__(
            parent,
            title_key="health_check.result.title",
            min_width=800,
            buttons="close",
        )
        self.setMinimumHeight(500)

    def _build_content(self, layout):
        # Main tabbed view
        issues = self._report.count_total_issues()

        if issues == 0:
            lbl = QLabel(t("health_check.result.no_issues"))
            lbl.setWordWrap(True)
            layout.addWidget(lbl)
            return

        summary = QLabel(
            t(
                "health_check.result.summary",
                total=self._report.total_games,
                issues=issues,
            )
        )
        summary.setWordWrap(True)
        layout.addWidget(summary)

        tabs = QTabWidget()

        tabs.addTab(self._mk_store_tab(), t("health_check.tabs.store"))
        tabs.addTab(self._mk_data_tab(), t("health_check.tabs.data"))
        tabs.addTab(self._mk_cache_tab(), t("health_check.tabs.cache"))

        layout.addWidget(tabs)

    def _mk_store_tab(self):
        # Store availability table
        w = QWidget()
        vbox = QVBoxLayout(w)

        rows = self._report.store_unavailable
        if not rows:
            vbox.addWidget(QLabel(t("health_check.result.no_issues")))
            return w

        tbl = QTableWidget(len(rows), 4)
        tbl.setHorizontalHeaderLabels(["App ID", "Name", "Status", "Details"])
        tbl.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        tbl.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)

        hdr = tbl.horizontalHeader()
        if hdr:
            hdr.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
            hdr.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
            hdr.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
            hdr.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)

        for idx, result in enumerate(rows):
            tbl.setItem(idx, 0, QTableWidgetItem(str(result.app_id)))
            tbl.setItem(idx, 1, QTableWidgetItem(result.name))

            icon = t(_STATUS_EMOJI_KEYS.get(result.status, "emoji.white_circle"))
            status_txt = t("health_check.store_status.%s" % result.status)
            item = QTableWidgetItem("%s %s" % (icon, status_txt))
            item.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            tbl.setItem(idx, 2, item)

            tbl.setItem(idx, 3, QTableWidgetItem(result.details))

        vbox.addWidget(tbl)
        return w

    def _mk_data_tab(self):
        # Missing data summary
        w = QWidget()
        vbox = QVBoxLayout(w)

        vbox.addWidget(QLabel(t("health_check.data_status.missing_metadata", count=len(self._report.missing_metadata))))
        vbox.addWidget(QLabel(t("health_check.data_status.missing_artwork", count=len(self._report.missing_artwork))))
        vbox.addWidget(QLabel(t("health_check.data_status.ghost_apps", count=len(self._report.ghost_apps))))
        vbox.addStretch()
        return w

    def _mk_cache_tab(self):
        # Cache freshness counts
        w = QWidget()
        vbox = QVBoxLayout(w)

        vbox.addWidget(QLabel(t("health_check.cache_status.stale_hltb", count=self._report.stale_hltb)))
        vbox.addWidget(QLabel(t("health_check.cache_status.stale_protondb", count=self._report.stale_protondb)))
        vbox.addStretch()
        return w
