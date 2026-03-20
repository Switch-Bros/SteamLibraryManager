#
# steam_library_manager/ui/dialogs/statistics_dialog.py
# Library statistics and enrichment coverage
#
# Copyright © 2025-2026 SwitchBros
# Licensed under the MIT License. See LICENSE for details.
#

from __future__ import annotations

from collections import Counter

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

from steam_library_manager.utils.i18n import t

__all__ = ["StatisticsDialog"]


class StatisticsDialog(QDialog):
    """Library stats in four tabs: overview, genre, platform, top 10."""

    def __init__(self, parent):
        super().__init__(parent)
        self.setWindowTitle(t("ui.stats.title"))
        self.setMinimumSize(600, 500)

        gm = parent.game_manager
        self._games = gm.get_library_entries() if gm else []

        lay = QVBoxLayout(self)
        tabs = QTabWidget()

        tabs.addTab(self._overview(), t("ui.stats.tab_overview"))
        tabs.addTab(self._genres(), t("ui.stats.tab_genre"))
        tabs.addTab(self._platforms(), t("ui.stats.tab_platform"))
        tabs.addTab(self._top10(), t("ui.stats.tab_top10"))

        lay.addWidget(tabs)

    # -- tabs --

    def _overview(self):
        w = QWidget()
        lay = QVBoxLayout(w)

        total = len(self._games)
        inst = sum(1 for g in self._games if g.installed)
        pt_total = sum(g.playtime_minutes for g in self._games)
        pt_avg = pt_total / total if total > 0 else 0

        cats = set()
        for g in self._games:
            cats.update(g.categories)

        rows = [
            (t("ui.stats.total_games"), str(total)),
            (t("ui.stats.installed_games"), str(inst)),
            (t("ui.stats.total_categories"), str(len(cats))),
            (t("ui.stats.total_playtime"), t("ui.stats.hours_unit", hours=round(pt_total / 60, 1))),
            (t("ui.stats.avg_playtime"), t("ui.stats.hours_unit", hours=round(pt_avg / 60, 1))),
        ]

        for lbl, val in rows:
            r = QHBoxLayout()
            r.addWidget(QLabel("<b>%s:</b>" % lbl))
            r.addStretch()
            v = QLabel(val)
            v.setAlignment(Qt.AlignmentFlag.AlignRight)
            r.addWidget(v)
            lay.addLayout(r)

        lay.addStretch()
        return w

    def _genres(self):
        cnt = Counter()
        for g in self._games:
            for genre in g.genres:
                cnt[genre] += 1
        return self._bar_list(cnt)

    def _platforms(self):
        cnt = Counter()
        for g in self._games:
            for p in g.platforms:
                cnt[p.capitalize()] += 1
        return self._bar_list(cnt)

    def _top10(self):
        w = QWidget()
        lay = QVBoxLayout(w)

        top = sorted(self._games, key=lambda g: g.playtime_minutes, reverse=True)[:10]

        if not top:
            nd = QLabel(t("ui.stats.no_data"))
            nd.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lay.addWidget(nd)
            lay.addStretch()
            return w

        for i, g in enumerate(top, 1):
            r = QHBoxLayout()
            rk = QLabel("<b>#%d</b>" % i)
            rk.setFixedWidth(30)
            nm = QLabel(g.name)
            nm.setToolTip("App ID: %s" % g.app_id)
            hrs = round(g.playtime_minutes / 60, 1)
            pt = QLabel(t("ui.stats.hours_unit", hours=hrs))
            pt.setAlignment(Qt.AlignmentFlag.AlignRight)
            pt.setFixedWidth(80)

            r.addWidget(rk)
            r.addWidget(nm, stretch=1)
            r.addWidget(pt)
            lay.addLayout(r)

        lay.addStretch()
        return w

    # -- helpers --

    @staticmethod
    def _bar_list(counter):
        # scrollable bar chart from Counter
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        inner = QWidget()
        lay = QVBoxLayout(inner)

        if not counter:
            nd = QLabel(t("ui.stats.no_data"))
            nd.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lay.addWidget(nd)
            lay.addStretch()
            scroll.setWidget(inner)
            return scroll

        mx = max(counter.values()) if counter else 1

        for lbl, cnt in counter.most_common():
            r = QHBoxLayout()
            lb = QLabel(lbl)
            lb.setFixedWidth(150)

            bw = int((cnt / mx) * 200) if mx > 0 else 0
            bar = QLabel()
            bar.setFixedSize(bw, 16)
            bar.setStyleSheet("background-color: #1a9fff; border-radius: 3px;")

            c = QLabel(str(cnt))
            c.setFixedWidth(40)
            c.setAlignment(Qt.AlignmentFlag.AlignRight)

            r.addWidget(lb)
            r.addWidget(bar)
            r.addStretch()
            r.addWidget(c)
            lay.addLayout(r)

        lay.addStretch()
        scroll.setWidget(inner)
        return scroll
