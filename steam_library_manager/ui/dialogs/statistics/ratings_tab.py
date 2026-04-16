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
from steam_library_manager.utils.i18n import t

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
        for s in pegi:
            if s.label == "none":
                s.label = t("common.no_rating")
            elif s.label.isdigit():
                s.label = "PEGI %s" % s.label
        d1 = DonutChart()
        d1.set_data(pegi)
        d1.setMinimumSize(280, 250)
        row1.addWidget(d1, stretch=1)

        reviews = svc.review_buckets()
        _review_map = {
            "op_95": "95%%+ (%s)" % t("ui.reviews.overwhelmingly_positive"),
            "vp_80": "80-94%% (%s)" % t("ui.reviews.very_positive"),
            "pos_70": "70-79%% (%s)" % t("ui.reviews.positive"),
            "mixed_40": "40-69%% (%s)" % t("ui.reviews.mixed"),
            "neg_0": "0-39%% (%s)" % t("ui.reviews.negative"),
            "no_reviews": t("ui.reviews.no_reviews"),
        }
        for s in reviews:
            s.label = _review_map.get(s.label, s.label)
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
