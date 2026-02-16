# src/ui/dialogs/statistics_dialog.py

"""Statistics dialog with four tab views for library analytics.

Provides Overview, By Genre, By Platform, and Top 10 Most Played tabs
using data from the GameManager's query service.
"""

from __future__ import annotations

from collections import Counter
from typing import TYPE_CHECKING

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from src.utils.i18n import t

if TYPE_CHECKING:
    from src.core.game import Game
    from src.ui.main_window import MainWindow

__all__ = ["StatisticsDialog"]


class StatisticsDialog(QDialog):
    """Dialog showing library statistics in four tab views.

    Attributes:
        _games: List of real games used for all statistics.
    """

    def __init__(self, parent: MainWindow) -> None:
        """Initializes the StatisticsDialog.

        Args:
            parent: The MainWindow instance providing game data.
        """
        super().__init__(parent)
        self.setWindowTitle(t("ui.stats.title"))
        self.setMinimumSize(600, 500)

        gm = parent.game_manager
        self._games: list[Game] = gm.get_real_games() if gm else []

        layout = QVBoxLayout(self)
        tabs = QTabWidget()

        tabs.addTab(self._build_overview_tab(), t("ui.stats.tab_overview"))
        tabs.addTab(self._build_genre_tab(), t("ui.stats.tab_genre"))
        tabs.addTab(self._build_platform_tab(), t("ui.stats.tab_platform"))
        tabs.addTab(self._build_top10_tab(), t("ui.stats.tab_top10"))

        layout.addWidget(tabs)

    # ------------------------------------------------------------------
    # Tab builders
    # ------------------------------------------------------------------

    def _build_overview_tab(self) -> QWidget:
        """Builds the overview tab showing aggregate statistics.

        Returns:
            Widget containing the overview layout.
        """
        widget = QWidget()
        layout = QVBoxLayout(widget)

        total = len(self._games)
        installed = sum(1 for g in self._games if g.installed)
        total_playtime = sum(g.playtime_minutes for g in self._games)
        avg_playtime = total_playtime / total if total > 0 else 0

        categories: set[str] = set()
        for g in self._games:
            categories.update(g.categories)
        cat_count = len(categories)

        stats = [
            (t("ui.stats.total_games"), str(total)),
            (t("ui.stats.installed_games"), str(installed)),
            (t("ui.stats.total_categories"), str(cat_count)),
            (t("ui.stats.total_playtime"), t("ui.stats.hours_unit", hours=round(total_playtime / 60, 1))),
            (t("ui.stats.avg_playtime"), t("ui.stats.hours_unit", hours=round(avg_playtime / 60, 1))),
        ]

        for label_text, value_text in stats:
            row = QHBoxLayout()
            label = QLabel(f"<b>{label_text}:</b>")
            value = QLabel(value_text)
            value.setAlignment(Qt.AlignmentFlag.AlignRight)
            row.addWidget(label)
            row.addStretch()
            row.addWidget(value)
            layout.addLayout(row)

        layout.addStretch()
        return widget

    def _build_genre_tab(self) -> QWidget:
        """Builds the genre distribution tab.

        Returns:
            Scrollable widget showing genre counts sorted descending.
        """
        genre_counter: Counter[str] = Counter()
        for g in self._games:
            for genre in g.genres:
                genre_counter[genre] += 1

        return self._build_bar_list(genre_counter)

    def _build_platform_tab(self) -> QWidget:
        """Builds the platform distribution tab.

        Returns:
            Scrollable widget showing platform counts sorted descending.
        """
        platform_counter: Counter[str] = Counter()
        for g in self._games:
            for plat in g.platforms:
                platform_counter[plat.capitalize()] += 1

        return self._build_bar_list(platform_counter)

    def _build_top10_tab(self) -> QWidget:
        """Builds the top 10 most played games tab.

        Returns:
            Widget showing the top 10 games by playtime.
        """
        widget = QWidget()
        layout = QVBoxLayout(widget)

        sorted_games = sorted(self._games, key=lambda g: g.playtime_minutes, reverse=True)[:10]

        if not sorted_games:
            no_data = QLabel(t("ui.stats.no_data"))
            no_data.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(no_data)
            layout.addStretch()
            return widget

        for i, game in enumerate(sorted_games, 1):
            row = QHBoxLayout()
            rank = QLabel(f"<b>#{i}</b>")
            rank.setFixedWidth(30)
            name = QLabel(game.name)
            name.setToolTip(f"App ID: {game.app_id}")
            hours = round(game.playtime_minutes / 60, 1)
            playtime = QLabel(t("ui.stats.hours_unit", hours=hours))
            playtime.setAlignment(Qt.AlignmentFlag.AlignRight)
            playtime.setFixedWidth(80)

            row.addWidget(rank)
            row.addWidget(name, stretch=1)
            row.addWidget(playtime)
            layout.addLayout(row)

        layout.addStretch()
        return widget

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _build_bar_list(counter: Counter[str]) -> QWidget:
        """Builds a scrollable list of items with counts from a Counter.

        Args:
            counter: Counter mapping labels to counts.

        Returns:
            A scroll area widget with the bar list.
        """
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        inner = QWidget()
        layout = QVBoxLayout(inner)

        if not counter:
            no_data = QLabel(t("ui.stats.no_data"))
            no_data.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(no_data)
            layout.addStretch()
            scroll.setWidget(inner)
            return scroll

        max_count = max(counter.values()) if counter else 1

        for label_text, count in counter.most_common():
            row = QHBoxLayout()
            label = QLabel(label_text)
            label.setFixedWidth(150)

            bar_width = int((count / max_count) * 200) if max_count > 0 else 0
            bar = QLabel()
            bar.setFixedSize(bar_width, 16)
            bar.setStyleSheet("background-color: #1a9fff; border-radius: 3px;")

            count_label = QLabel(str(count))
            count_label.setFixedWidth(40)
            count_label.setAlignment(Qt.AlignmentFlag.AlignRight)

            row.addWidget(label)
            row.addWidget(bar)
            row.addStretch()
            row.addWidget(count_label)
            layout.addLayout(row)

        layout.addStretch()
        scroll.setWidget(inner)
        return scroll
