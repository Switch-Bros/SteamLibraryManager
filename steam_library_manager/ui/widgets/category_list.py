#
# steam_library_manager/ui/widgets/category_list.py
# Horizontal category list with checkbox items (single and tri-state).
#
# Copyright © 2025-2026 SwitchBros
# Licensed under the MIT License. See LICENSE for details.
#

from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal, QSize
from PyQt6.QtWidgets import (
    QListWidget,
    QListWidgetItem,
    QAbstractItemView,
    QCheckBox,
)

from steam_library_manager.ui.theme import Theme

__all__ = ["HorizontalCategoryList"]


class HorizontalCategoryList(QListWidget):
    """Wrapping list of category checkboxes (binary or tri-state)."""

    category_toggled = pyqtSignal(str, bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setViewMode(QListWidget.ViewMode.IconMode)
        self.setFlow(QListWidget.Flow.TopToBottom)
        self.setWrapping(True)
        self.setResizeMode(QListWidget.ResizeMode.Adjust)
        self.setSpacing(4)
        self.setUniformItemSizes(True)
        self.setMovement(QListWidget.Movement.Static)
        self.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setFixedHeight(190)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        self.games_categories: list[list[str]] = []

    def set_categories(self, all_categories: list[str], game_categories: list[str]) -> None:
        """Sets categories for a single game."""
        self.clear()
        if not all_categories:
            return
        for category in sorted(all_categories):
            if category == "favorite":
                continue
            item = QListWidgetItem(self)
            item.setSizeHint(QSize(200, 24))
            display_name = category.replace("&", "&&")
            cb = QCheckBox(display_name)
            cb.setChecked(category in game_categories)
            cb.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            cb.setStyleSheet("QCheckBox { font-size: 11px; margin-left: 2px; }")
            cb.stateChanged.connect(
                lambda state, c=category: self.category_toggled.emit(c, state == Qt.CheckState.Checked.value)
            )
            self.setItemWidget(item, cb)

    def set_categories_multi(self, all_categories: list[str], games_categories: list[list[str]]) -> None:
        """Sets categories for multiple games with tri-state checkboxes."""
        self.clear()
        if not all_categories or not games_categories:
            return

        self.games_categories = games_categories
        total_games = len(games_categories)

        for category in sorted(all_categories):
            if category == "favorite":
                continue

            count = sum(1 for game_cats in games_categories if category in game_cats)

            item = QListWidgetItem(self)
            item.setSizeHint(QSize(200, 24))
            display_name = category.replace("&", "&&")
            cb = QCheckBox(display_name)
            cb.setTristate(True)
            cb.setFocusPolicy(Qt.FocusPolicy.NoFocus)

            if count == 0:
                cb.setCheckState(Qt.CheckState.Unchecked)
                cb.setStyleSheet("QCheckBox { font-size: 11px; margin-left: 2px; }")
            elif count == total_games:
                cb.setCheckState(Qt.CheckState.Checked)
                color = Theme.CATEGORY_SELECTED
                cb.setStyleSheet(
                    f"QCheckBox {{ font-size: 11px; margin-left: 2px; color: {color}; font-weight: bold; }}"
                )
            else:
                cb.setCheckState(Qt.CheckState.PartiallyChecked)
                cb.setStyleSheet(f"QCheckBox {{ font-size: 11px; margin-left: 2px; color: {Theme.TEXT_MUTED}; }}")

            cb.setProperty("category", category)
            cb.setProperty("previous_state", cb.checkState())
            cb.clicked.connect(lambda _checked=None, checkbox=cb: self._handle_tristate_click(checkbox))
            self.setItemWidget(item, cb)

    def _handle_tristate_click(self, checkbox: QCheckBox) -> None:
        category = checkbox.property("category")
        previous_state = checkbox.property("previous_state")

        if previous_state == Qt.CheckState.Checked:
            checkbox.setCheckState(Qt.CheckState.Unchecked)
            checkbox.setStyleSheet("QCheckBox { font-size: 11px; margin-left: 2px; }")
            new_state = Qt.CheckState.Unchecked
            checked = False
        else:
            checkbox.setCheckState(Qt.CheckState.Checked)
            checkbox.setStyleSheet(
                "QCheckBox { font-size: 11px; margin-left: 2px; color: #FFD700; font-weight: bold; }"
            )
            new_state = Qt.CheckState.Checked
            checked = True

        checkbox.setProperty("previous_state", new_state)
        self.category_toggled.emit(category, checked)
