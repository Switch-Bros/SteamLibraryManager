#
# steam_library_manager/ui/dialogs/statistics/achievements_tab.py
# Achievement statistics: metrics, completion buckets, almost-done bar chart, trophy wall
#
# Copyright (c) 2025-2026 SwitchBros
# Licensed under the MIT License. See LICENSE for details.
#

from __future__ import annotations

import logging
import os

from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QColor, QPixmap
from PyQt6.QtWidgets import (
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from steam_library_manager.core.steam_assets import SteamAssets
from steam_library_manager.services.statistics_service import StatisticsService
from steam_library_manager.ui.theme import Theme
from steam_library_manager.ui.widgets.charts.bar_chart import BarChart
from steam_library_manager.ui.widgets.charts.donut_chart import DonutChart
from steam_library_manager.ui.widgets.metric_card import MetricCard
from steam_library_manager.utils.i18n import t

__all__ = ["AchievementsTab"]

logger = logging.getLogger("steamlibmgr.statistics")

_COMPLETION_COLORS = {
    "perfect": Theme.ACHV_GOLD,
    "almost": Theme.SUCCESS,
    "progress": Theme.ACCENT,
    "started": Theme.TXT_MUTED,
    "zero": Theme.DANGER,
    "none": Theme.BORDER,
}

_COVER_W = 120
_COVER_H = 180
_WALL_COLS = 5


class AchievementsTab(QWidget):
    def __init__(self, svc: StatisticsService, parent=None):
        super().__init__(parent)
        lay = QVBoxLayout(self)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        inner = QWidget()
        content = QVBoxLayout(inner)

        # -- metric cards row --
        cards_row = QHBoxLayout()
        rare = svc.rare_achievements()
        perfect_count = len(svc.perfect_games())

        cards_row.addWidget(
            MetricCard(
                "\U0001f3c6",
                t("stats.achievements.total_unlocked"),
                str(rare["total_unlocked"]),
                accent_color=Theme.ACCENT,
            )
        )
        cards_row.addWidget(
            MetricCard(
                "\U0001f48e",
                t("stats.achievements.rare"),
                str(rare["rare_count"]),
                accent_color=Theme.DANGER,
            )
        )
        cards_row.addWidget(
            MetricCard(
                "\u2b50",
                t("stats.achievements.ultra_rare"),
                str(rare["ultra_rare_count"]),
                accent_color="#9B59B6",
            )
        )
        cards_row.addWidget(
            MetricCard(
                "\U0001f947",
                t("stats.achievements.perfect"),
                str(perfect_count),
                accent_color=Theme.ACHV_GOLD,
            )
        )
        content.addLayout(cards_row)

        # -- charts row: completion buckets + almost-done bar --
        charts_row = QHBoxLayout()

        # completion buckets donut
        buckets = svc.achievement_buckets()
        for s in buckets:
            c = _COMPLETION_COLORS.get(s.label)
            if c:
                s.color = QColor(c)
        donut = DonutChart()
        donut.set_data(buckets)
        donut.setMinimumSize(280, 250)
        charts_row.addWidget(donut, stretch=1)

        # almost-done bar chart
        almost = svc.almost_done()
        if almost:
            bar_slices = []
            for g in almost[:10]:
                from steam_library_manager.services.chart_data import ChartSlice

                bar_slices.append(
                    ChartSlice(
                        label=g.name,
                        value=g.achievement_percentage,
                        color=QColor(Theme.SUCCESS),
                    )
                )
            bar = BarChart()
            bar.set_data(bar_slices)
            bar.setMinimumSize(300, 250)
            charts_row.addWidget(bar, stretch=1)

        content.addLayout(charts_row)

        # -- trophy wall --
        perfect_games = svc.perfect_games()
        if perfect_games:
            wall_label = QLabel(t("stats.achievements.trophy_wall"))
            wall_label.setStyleSheet("font-size: 14px; font-weight: bold; margin-top: 12px;")
            content.addWidget(wall_label)

            wall = QGridLayout()
            wall.setSpacing(8)
            for i, g in enumerate(perfect_games):
                row = i // _WALL_COLS
                col = i % _WALL_COLS
                thumb = self._make_cover(g)
                wall.addWidget(thumb, row, col)
            content.addLayout(wall)
        else:
            no_lbl = QLabel(t("stats.achievements.no_perfect"))
            no_lbl.setStyleSheet("color: %s; font-style: italic; padding: 8px;" % Theme.TXT_MUTED)
            content.addWidget(no_lbl)

        scroll.setWidget(inner)
        lay.addWidget(scroll)

    def _make_cover(self, game) -> QWidget:
        """Build a thumbnail widget with gold border for a perfect game."""
        container = QWidget()
        container.setFixedSize(_COVER_W + 8, _COVER_H + 28)
        container.setStyleSheet(
            "border: 2px solid %s; border-radius: 4px; background: %s;" % (Theme.ACHV_GOLD, Theme.BG_SEC)
        )
        box = QVBoxLayout(container)
        box.setContentsMargins(2, 2, 2, 2)
        box.setSpacing(2)

        img_label = QLabel()
        img_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        img_label.setFixedSize(_COVER_W, _COVER_H)
        img_label.setStyleSheet("border: none;")

        path = SteamAssets.get_asset_path(game.app_id, "grids")
        loaded = False

        # try local file first
        if path and not path.startswith("http") and os.path.isfile(path):
            pm = QPixmap(path)
            if not pm.isNull():
                img_label.setPixmap(
                    pm.scaled(
                        QSize(_COVER_W, _COVER_H),
                        Qt.AspectRatioMode.KeepAspectRatio,
                        Qt.TransformationMode.SmoothTransformation,
                    )
                )
                loaded = True

        # fallback: download CDN URL
        if not loaded and path and path.startswith("http"):
            try:
                import requests

                resp = requests.get(path, timeout=5)
                if resp.status_code == 200:
                    pm = QPixmap()
                    pm.loadFromData(resp.content)
                    if not pm.isNull():
                        img_label.setPixmap(
                            pm.scaled(
                                QSize(_COVER_W, _COVER_H),
                                Qt.AspectRatioMode.KeepAspectRatio,
                                Qt.TransformationMode.SmoothTransformation,
                            )
                        )
                        loaded = True
            except Exception:
                pass

        if not loaded:
            img_label.setText(game.name[:20])
            img_label.setWordWrap(True)
            img_label.setStyleSheet("border: none; color: %s; font-size: 10px;" % Theme.TXT_PRI)

        box.addWidget(img_label)

        name_label = QLabel(game.name)
        name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        name_label.setFixedWidth(_COVER_W)
        name_label.setStyleSheet("border: none; color: %s; font-size: 9px;" % Theme.TXT_PRI)
        name_label.setWordWrap(True)
        name_label.setMaximumHeight(20)
        box.addWidget(name_label)

        container.setToolTip(game.name)
        return container
