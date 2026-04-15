from __future__ import annotations

from PyQt6.QtWidgets import QHBoxLayout, QVBoxLayout, QWidget

from steam_library_manager.services.statistics_service import StatisticsService
from steam_library_manager.ui.theme import Theme
from steam_library_manager.ui.widgets.charts.bar_chart import BarChart
from steam_library_manager.ui.widgets.charts.donut_chart import DonutChart
from steam_library_manager.ui.widgets.metric_card import MetricCard
from steam_library_manager.utils.i18n import t

__all__ = ["OverviewTab"]


class OverviewTab(QWidget):
    def __init__(self, svc: StatisticsService, parent=None):
        super().__init__(parent)
        data = svc.overview()
        lay = QVBoxLayout(self)

        # metric cards row
        cards = QHBoxLayout()
        cards.setSpacing(12)
        cards.addWidget(
            MetricCard(
                "\U0001f3ae",
                t("ui.stats.total_games"),
                str(data["total"]),
                sub_info=t("stats.overview.installed_count", installed=data["installed"]),
                accent_color=Theme.ACCENT,
            )
        )
        cards.addWidget(
            MetricCard(
                "\U0001f551",
                t("ui.stats.total_playtime"),
                "%s h" % data["playtime_hours"],
                sub_info=t("stats.overview.avg_label", hours=data["avg_playtime_hours"]),
                accent_color=Theme.SUCCESS,
            )
        )
        cards.addWidget(
            MetricCard(
                "\U0001f47b",
                t("stats.overview.never_played"),
                str(data["never_played"]),
                sub_info="%s%%" % data["never_played_pct"],
                accent_color=Theme.WARNING,
            )
        )
        cards.addWidget(
            MetricCard(
                "\U0001f3c6",
                t("stats.overview.perfect_games"),
                str(data["perfect_games"]),
                accent_color=Theme.ACHV_GOLD,
            )
        )
        lay.addLayout(cards)

        # charts row
        genre_data = svc.genres_by_count(top_n=8)
        top_data = svc.top_played(n=5)
        # only show top played if there's actual playtime
        top_data = [s for s in top_data if s.value > 0]

        if genre_data or top_data:
            charts = QHBoxLayout()
            if genre_data:
                donut = DonutChart()
                donut.set_data(genre_data)
                charts.addWidget(donut, stretch=1)
            if top_data:
                bar = BarChart()
                bar.set_data(top_data)
                charts.addWidget(bar, stretch=1)
            lay.addLayout(charts, stretch=1)
        else:
            lay.addStretch()
