#
# steam_library_manager/ui/dialogs/statistics/statistics_dialog.py
# Tabbed statistics dialog - shell that lazy-loads tab modules
#
# Copyright (c) 2025-2026 SwitchBros
# Licensed under the MIT License. See LICENSE for details.
#

from __future__ import annotations

from PyQt6.QtWidgets import QTabWidget, QVBoxLayout

from steam_library_manager.ui.widgets.base_dialog import BaseDialog
from steam_library_manager.utils.i18n import t

__all__ = ["StatisticsDialog"]


class StatisticsDialog(BaseDialog):
    """Library statistics in four tabs: overview, genre, platform, achievements."""

    def __init__(self, parent):
        self._mw = parent
        gm = parent.game_manager
        self._games = gm.get_library_entries() if gm else []
        self._database = getattr(parent, "game_service", None)
        if self._database:
            self._database = getattr(self._database, "database", None)
        super().__init__(
            parent,
            title_key="ui.stats.title",
            min_width=720,
            buttons="none",
            show_title_label=False,
        )
        self.setMinimumHeight(520)

    def _build_content(self, layout: QVBoxLayout):
        from steam_library_manager.services.statistics_service import StatisticsService
        from steam_library_manager.ui.dialogs.statistics.overview_tab import OverviewTab
        from steam_library_manager.ui.dialogs.statistics.genre_tab import GenreTab
        from steam_library_manager.ui.dialogs.statistics.platform_tab import PlatformTab
        from steam_library_manager.ui.dialogs.statistics.achievements_tab import AchievementsTab

        svc = StatisticsService(self._games, database=self._database)

        tabs = QTabWidget()
        tabs.addTab(OverviewTab(svc, self), t("common.overview"))
        tabs.addTab(GenreTab(svc, self), t("ui.stats.tab_genre"))
        tabs.addTab(PlatformTab(svc, self), t("ui.stats.tab_platform"))
        tabs.addTab(AchievementsTab(svc, self), t("ui.stats.tab_achievements"))
        layout.addWidget(tabs)
