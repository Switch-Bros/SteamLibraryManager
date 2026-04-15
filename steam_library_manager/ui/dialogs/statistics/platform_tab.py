#
# steam_library_manager/ui/dialogs/statistics/platform_tab.py
# Platform, Deck compatibility and ProtonDB donut charts
#
# Copyright (c) 2025-2026 SwitchBros
# Licensed under the MIT License. See LICENSE for details.
#

from __future__ import annotations

from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import QHBoxLayout, QScrollArea, QVBoxLayout, QWidget

from steam_library_manager.services.statistics_service import StatisticsService
from steam_library_manager.ui.theme import Theme
from steam_library_manager.ui.widgets.charts.donut_chart import DonutChart

__all__ = ["PlatformTab"]

_PLATFORM_COLORS = {
    "Windows": "#0078D4",
    "Linux": "#FDE100",
    "Mac": "#A2AAAD",
}


class PlatformTab(QWidget):
    def __init__(self, svc: StatisticsService, parent=None):
        super().__init__(parent)
        lay = QVBoxLayout(self)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        inner = QWidget()
        row = QHBoxLayout(inner)

        # platform donut
        plat = svc.platforms()
        for s in plat:
            c = _PLATFORM_COLORS.get(s.label)
            if c:
                s.color = QColor(c)
        d1 = DonutChart()
        d1.set_data(plat)
        d1.setMinimumSize(220, 200)
        row.addWidget(d1, stretch=1)

        # deck compatibility donut
        deck = svc.deck_status()
        for s in deck:
            c = Theme.DECK_COLORS.get(s.label)
            if c:
                s.color = QColor(c)
        d2 = DonutChart()
        d2.set_data(deck)
        d2.setMinimumSize(220, 200)
        row.addWidget(d2, stretch=1)

        # protondb tier donut
        pdb = svc.protondb_tiers()
        for s in pdb:
            c = Theme.PDB_COLORS.get(s.label)
            if c:
                s.color = QColor(c)
        d3 = DonutChart()
        d3.set_data(pdb)
        d3.setMinimumSize(220, 200)
        row.addWidget(d3, stretch=1)

        scroll.setWidget(inner)
        lay.addWidget(scroll)
