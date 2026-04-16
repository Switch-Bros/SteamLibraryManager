#
# steam_library_manager/ui/dialogs/statistics/playtime_tab.py
# Playtime statistics: metrics, buckets donut, top played bar, HLTB, shame pile
#
# Copyright (c) 2025-2026 SwitchBros
# Licensed under the MIT License. See LICENSE for details.
#

from __future__ import annotations

from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import QHBoxLayout, QScrollArea, QVBoxLayout, QWidget

from steam_library_manager.services.statistics_service import StatisticsService
from steam_library_manager.ui.theme import Theme
from steam_library_manager.ui.widgets.charts.bar_chart import BarChart
from steam_library_manager.ui.widgets.charts.donut_chart import DonutChart
from steam_library_manager.ui.widgets.metric_card import MetricCard
from steam_library_manager.utils.i18n import t

__all__ = ["PlaytimeTab"]

_PLAYTIME_LABELS = {
    "0h": "0 h",
    "lt_1h": "< 1 h",
    "1_5h": "1 - 5 h",
    "5_20h": "5 - 20 h",
    "20_100h": "20 - 100 h",
    "100h_plus": "100+ h",
}

_HLTB_LABELS_STATIC = {
    "lt_5h": "< 5 h",
    "5_10h": "5 - 10 h",
    "10_20h": "10 - 20 h",
    "20_40h": "20 - 40 h",
    "40_100h": "40 - 100 h",
    "100h_plus": "100+ h",
}


class PlaytimeTab(QWidget):
    def __init__(self, svc: StatisticsService, parent=None):
        super().__init__(parent)
        lay = QVBoxLayout(self)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        inner = QWidget()
        content = QVBoxLayout(inner)

        overview = svc.overview()
        shame = svc.shame_pile()

        # -- metric cards row --
        cards_row = QHBoxLayout()
        cards_row.addWidget(
            MetricCard(
                "\u23f1",
                t("ui.stats.total_playtime"),
                "{} h".format(overview["playtime_hours"]),
                accent_color=Theme.ACCENT,
            )
        )
        cards_row.addWidget(
            MetricCard(
                "\U0001f6ab",
                t("stats.overview.never_played"),
                str(overview["never_played"]),
                sub_info="{}%".format(overview["never_played_pct"]),
                accent_color=Theme.DANGER,
            )
        )
        cards_row.addWidget(
            MetricCard(
                "\U0001f4e6",
                t("stats.playtime.shame_pile"),
                str(shame["installed"]),
                sub_info=t("stats.playtime.shame_installed"),
                accent_color=Theme.WARNING,
            )
        )
        cards_row.addWidget(
            MetricCard(
                "\U0001f4ca",
                t("stats.playtime.avg_per_game"),
                "{} h".format(overview["avg_playtime_hours"]),
                accent_color=Theme.SUCCESS,
            )
        )
        content.addLayout(cards_row)

        # -- row 1: playtime buckets donut + top 5 most played bar --
        row1 = QHBoxLayout()

        buckets = svc.playtime_buckets()
        for s in buckets:
            s.label = _PLAYTIME_LABELS.get(s.label, s.label)
        donut1 = DonutChart()
        donut1.set_data(buckets)
        donut1.setMinimumSize(280, 250)
        row1.addWidget(donut1, stretch=1)

        top_played = [s for s in svc.top_played(n=5) if s.value > 0]
        if top_played:
            for s in top_played:
                s.color = QColor(Theme.ACCENT)
            bar1 = BarChart()
            bar1.set_data(top_played)
            bar1.setMinimumSize(300, 250)
            row1.addWidget(bar1, stretch=1)

        content.addLayout(row1)

        # -- row 2: HLTB buckets donut + shame pile bar --
        row2 = QHBoxLayout()

        hltb = svc.hltb_buckets()
        hltb_labels = dict(_HLTB_LABELS_STATIC)
        hltb_labels["no_data"] = t("ui.stats.no_data")
        for s in hltb:
            s.label = hltb_labels.get(s.label, s.label)
        donut2 = DonutChart()
        donut2.set_data(hltb)
        donut2.setMinimumSize(280, 250)
        row2.addWidget(donut2, stretch=1)

        shame_games = svc.shame_pile_games(n=5)
        if shame_games:
            for s in shame_games:
                s.color = QColor(Theme.WARNING)
            bar2 = BarChart()
            bar2.set_data(shame_games)
            bar2.setMinimumSize(300, 250)
            row2.addWidget(bar2, stretch=1)

        content.addLayout(row2)

        scroll.setWidget(inner)
        lay.addWidget(scroll)
