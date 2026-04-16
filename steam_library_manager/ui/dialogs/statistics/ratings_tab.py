#
# steam_library_manager/ui/dialogs/statistics/ratings_tab.py
# Ratings statistics: PEGI distribution, review scores, top developers
#
# Copyright (c) 2025-2026 SwitchBros
# Licensed under the MIT License. See LICENSE for details.
#

from __future__ import annotations

from PyQt6.QtWidgets import QHBoxLayout, QScrollArea, QVBoxLayout, QWidget

from steam_library_manager.services.statistics_service import StatisticsService
from steam_library_manager.ui.widgets.charts.bar_chart import BarChart
from steam_library_manager.ui.widgets.charts.donut_chart import DonutChart

__all__ = ["RatingsTab"]


class RatingsTab(QWidget):
    def __init__(self, svc: StatisticsService, parent=None):
        super().__init__(parent)
        lay = QVBoxLayout(self)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        inner = QWidget()
        content = QVBoxLayout(inner)

        # -- row 1: PEGI donut + review score donut --
        row1 = QHBoxLayout()

        pegi = svc.pegi_distribution()
        d1 = DonutChart()
        d1.set_data(pegi)
        d1.setMinimumSize(280, 250)
        row1.addWidget(d1, stretch=1)

        reviews = svc.review_buckets()
        d2 = DonutChart()
        d2.set_data(reviews)
        d2.setMinimumSize(280, 250)
        row1.addWidget(d2, stretch=1)

        content.addLayout(row1)

        # -- row 2: top 10 developers bar chart --
        devs = svc.top_developers(n=10)
        if devs:
            bar = BarChart()
            bar.set_data(devs)
            bar.setMinimumSize(600, 300)
            content.addWidget(bar)

        content.addStretch()

        scroll.setWidget(inner)
        lay.addWidget(scroll)
