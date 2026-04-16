#
# steam_library_manager/ui/dialogs/statistics/comparison_tab.py
# Side-by-side game comparison with autocomplete search
#
# Copyright (c) 2025-2026 SwitchBros
# Licensed under the MIT License. See LICENSE for details.
#

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import (
    QCompleter,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QScrollArea,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from steam_library_manager.ui.theme import Theme
from steam_library_manager.utils.i18n import t

if TYPE_CHECKING:
    from steam_library_manager.core.game import Game

__all__ = ["ComparisonTab"]

_METRICS = [
    ("Playtime", lambda g: "{} h".format(round(g.playtime_minutes / 60, 1))),
    (
        "Achievements",
        lambda g: (
            "{}% ({}/{})".format(round(g.achievement_percentage, 1), g.achievement_unlocked, g.achievement_total)
            if g.achievement_total > 0
            else "-"
        ),
    ),
    ("Developer", lambda g: g.developer or "-"),
    ("Platforms", lambda g: ", ".join(g.platforms) if g.platforms else "-"),
    ("Deck Status", lambda g: g.steam_deck_status or "-"),
    ("ProtonDB", lambda g: g.proton_db_rating or "-"),
    ("HLTB (Main)", lambda g: "{} h".format(g.hltb_main_story) if g.hltb_main_story > 0 else "-"),
    ("PEGI", lambda g: g.pegi_rating or "-"),
]


def _display_name(game: Game, duplicates: set[str]) -> str:
    """Return game name, appending release year if name is duplicate."""
    name = game.name
    if name in duplicates and game.release_year > 0:
        try:
            year = datetime.fromtimestamp(game.release_year).year
            return "{} ({})".format(name, year)
        except (OSError, ValueError):
            pass
    return name


class ComparisonTab(QWidget):
    def __init__(self, games: list[Game], parent=None):
        super().__init__(parent)
        self._games = games

        # detect duplicate names
        name_counts: dict[str, int] = {}
        for g in games:
            name_counts[g.name] = name_counts.get(g.name, 0) + 1
        self._duplicate_names = {n for n, c in name_counts.items() if c > 1}

        # build lookup: display_name -> game
        self._games_by_name: dict[str, Game] = {}
        for g in games:
            dn = _display_name(g, self._duplicate_names)
            self._games_by_name[dn] = g

        self._game_names = sorted(self._games_by_name.keys(), key=str.lower)

        lay = QVBoxLayout(self)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        inner = QWidget()
        content = QVBoxLayout(inner)

        # -- search row --
        search_row = QHBoxLayout()

        self._left_edit = QLineEdit()
        self._left_edit.setPlaceholderText(t("stats.comparison.search_left"))
        left_completer = QCompleter(self._game_names)
        left_completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        left_completer.setFilterMode(Qt.MatchFlag.MatchContains)
        self._left_edit.setCompleter(left_completer)
        self._left_edit.returnPressed.connect(self._update_comparison)
        left_completer.activated.connect(self._update_comparison)
        search_row.addWidget(self._left_edit)

        self._right_edit = QLineEdit()
        self._right_edit.setPlaceholderText(t("stats.comparison.search_right"))
        right_completer = QCompleter(self._game_names)
        right_completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        right_completer.setFilterMode(Qt.MatchFlag.MatchContains)
        self._right_edit.setCompleter(right_completer)
        self._right_edit.returnPressed.connect(self._update_comparison)
        right_completer.activated.connect(self._update_comparison)
        search_row.addWidget(self._right_edit)

        content.addLayout(search_row)

        # -- comparison table --
        self._table = QTableWidget(len(_METRICS), 3)
        self._table.setHorizontalHeaderLabels(["", "", ""])
        self._table.verticalHeader().setVisible(False)
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table.setSelectionMode(QTableWidget.SelectionMode.NoSelection)
        header = self._table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self._table.setStyleSheet(
            "QTableWidget { background: %s; color: %s; gridline-color: %s; }"
            % (Theme.BG_SEC, Theme.TXT_PRI, Theme.BORDER)
        )

        for row_idx, (label, _) in enumerate(_METRICS):
            item = QTableWidgetItem(label)
            item.setForeground(QColor(Theme.TXT_MUTED))
            self._table.setItem(row_idx, 0, item)
            self._table.setItem(row_idx, 1, QTableWidgetItem("-"))
            self._table.setItem(row_idx, 2, QTableWidgetItem("-"))

        content.addWidget(self._table)

        self._hint = QLabel(t("stats.comparison.search_left"))
        self._hint.setStyleSheet("color: %s; font-style: italic; padding: 4px;" % Theme.TXT_MUTED)
        content.addWidget(self._hint)
        content.addStretch()

        scroll.setWidget(inner)
        lay.addWidget(scroll)

    def _update_comparison(self):
        left_name = self._left_edit.text().strip()
        right_name = self._right_edit.text().strip()

        left_game = self._games_by_name.get(left_name)
        right_game = self._games_by_name.get(right_name)

        for row_idx, (_, fn) in enumerate(_METRICS):
            left_val = fn(left_game) if left_game else "-"
            right_val = fn(right_game) if right_game else "-"
            self._table.setItem(row_idx, 1, QTableWidgetItem(left_val))
            self._table.setItem(row_idx, 2, QTableWidgetItem(right_val))

        if left_game and right_game:
            self._hint.hide()
        else:
            self._hint.show()
