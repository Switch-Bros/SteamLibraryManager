from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import QHBoxLayout, QLabel, QVBoxLayout, QWidget

from steam_library_manager.services.chart_data import CHART_PALETTE
from steam_library_manager.services.statistics_service import StatisticsService
from steam_library_manager.ui.theme import Theme
from steam_library_manager.ui.widgets.charts.donut_chart import DonutChart
from steam_library_manager.utils.i18n import t

__all__ = ["GenreTab"]


class GenreTab(QWidget):
    def __init__(self, svc: StatisticsService, parent=None):
        super().__init__(parent)
        lay = QVBoxLayout(self)

        count_data = svc.genres_by_count(top_n=8)
        time_data = svc.genres_by_playtime(top_n=8)

        if not count_data and not time_data:
            empty = QLabel(t("ui.stats.no_data"))
            empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            empty.setStyleSheet("color: %s; padding: 40px;" % Theme.TXT_MUTED)
            lay.addWidget(empty)
            return

        # consistent colors: same genre = same color in both donuts
        all_genres = []
        for s in count_data + time_data:
            if s.label not in all_genres:
                all_genres.append(s.label)
        color_map = {g: QColor(CHART_PALETTE[i % len(CHART_PALETTE)]) for i, g in enumerate(all_genres)}
        for s in count_data:
            s.color = color_map.get(s.label)
        for s in time_data:
            s.color = color_map.get(s.label)

        # two donuts side by side
        donuts = QHBoxLayout()
        d_count = DonutChart()
        d_count.set_data(count_data)
        donuts.addWidget(d_count, stretch=1)

        d_time = DonutChart()
        d_time.set_data(time_data)
        donuts.addWidget(d_time, stretch=1)

        lay.addLayout(donuts, stretch=1)

        # insight text
        if count_data and time_data:
            top_owned = count_data[0].label
            top_played = time_data[0].label
            if top_owned != top_played:
                txt = t("stats.genre.insight_mismatch", owned=top_owned, played=top_played)
            else:
                txt = t("stats.genre.insight_match", genre=top_owned)
            insight = QLabel(txt)
            insight.setAlignment(Qt.AlignmentFlag.AlignCenter)
            insight.setStyleSheet("color: %s; font-style: italic; padding: 8px;" % Theme.TXT_MUTED)
            lay.addWidget(insight)
