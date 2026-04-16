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

# readable labels for review bucket keys
_REVIEW_LABELS = {
    "op_95": "95%+ (Overwhelmingly Positive)",
    "vp_80": "80-94% (Very Positive)",
    "pos_70": "70-79% (Positive)",
    "mixed_40": "40-69% (Mixed)",
    "neg_0": "0-39% (Negative)",
    "no_reviews": "No Reviews",
}

# readable PEGI labels
_PEGI_LABELS = {
    "3": "PEGI 3",
    "7": "PEGI 7",
    "12": "PEGI 12",
    "16": "PEGI 16",
    "18": "PEGI 18",
    "none": "No Rating",
}


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
        for s in pegi:
            s.label = _PEGI_LABELS.get(s.label, "PEGI %s" % s.label)
        d1 = DonutChart()
        d1.set_data(pegi)
        d1.setMinimumSize(280, 250)
        row1.addWidget(d1, stretch=1)

        reviews = svc.review_buckets()
        for s in reviews:
            s.label = _REVIEW_LABELS.get(s.label, s.label)
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
