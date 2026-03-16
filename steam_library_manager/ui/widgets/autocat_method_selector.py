#
# steam_library_manager/ui/widgets/autocat_method_selector.py
# Method selector widget for the auto-categorize dialog
#
# Copyright © 2025-2026 SwitchBros
# Licensed under the MIT License. See LICENSE for details.
#

from __future__ import annotations

from typing import Any

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import (
    QButtonGroup,
    QCheckBox,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QRadioButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from steam_library_manager.config import config
from steam_library_manager.utils.i18n import t

__all__ = ["AutoCatMethodSelector"]

# Method key → i18n checkbox label key
_METHOD_CHECKBOX_KEYS: tuple[tuple[str, str], ...] = (
    ("tags", "auto_categorize.option_tags"),
    ("publisher", "auto_categorize.by_publisher"),
    ("franchise", "auto_categorize.option_franchise"),
    ("genre", "auto_categorize.by_genre"),
    ("developer", "auto_categorize.by_developer"),
    ("platform", "auto_categorize.by_platform"),
    ("user_score", "auto_categorize.by_user_score"),
    ("hours_played", "auto_categorize.by_hours_played"),
    ("flags", "auto_categorize.by_flags"),
    ("vr", "auto_categorize.by_vr"),
    ("year", "auto_categorize.by_year"),
    ("hltb", "auto_categorize.by_hltb"),
    ("language", "auto_categorize.by_language"),
    ("deck_status", "auto_categorize.by_deck_status"),
    ("achievements", "auto_categorize.by_achievements"),
    ("pegi", "auto_categorize.by_pegi"),
    ("curator", "auto_categorize.by_curator"),
)


class AutoCatMethodSelector(QWidget):
    """Widget for selecting auto-categorization methods and scope."""

    methods_changed = pyqtSignal()

    def __init__(
        self,
        parent: QWidget | None,
        games_count: int,
        all_games_count: int,
        category_name: str | None = None,
    ) -> None:
        super().__init__(parent)
        self._games_count = games_count
        self._all_games_count = all_games_count
        self._category_name = category_name
        self._checkboxes: dict[str, QCheckBox] = {}

        self._create_ui()

    def _create_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        self._create_methods_group(layout)
        self._create_tags_settings(layout)
        self._create_scope_group(layout)

        self.estimate_label = QLabel()
        self.estimate_label.setWordWrap(True)
        self.estimate_label.setStyleSheet("color: gray; font-style: italic;")
        layout.addWidget(self.estimate_label)

        self._connect_signals()
        self._update_estimate()

    def _create_methods_group(self, parent_layout: QVBoxLayout) -> None:
        methods_group = QGroupBox(t("auto_categorize.method_group"))
        grid = QGridLayout()
        grid.setSpacing(4)

        cols = 3
        for i, (key, i18n_key) in enumerate(_METHOD_CHECKBOX_KEYS):
            cb = QCheckBox(t(i18n_key))
            self._checkboxes[key] = cb
            grid.addWidget(cb, i // cols, i % cols)

        self._checkboxes["tags"].setChecked(True)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        select_all_btn = QPushButton(t("auto_categorize.select_all"))
        select_all_btn.clicked.connect(self._select_all)
        btn_layout.addWidget(select_all_btn)

        deselect_all_btn = QPushButton(t("auto_categorize.deselect_all"))
        deselect_all_btn.clicked.connect(self._deselect_all)
        btn_layout.addWidget(deselect_all_btn)

        outer = QVBoxLayout()
        outer.addLayout(grid)
        outer.addLayout(btn_layout)

        methods_group.setLayout(outer)
        parent_layout.addWidget(methods_group)

    def _create_tags_settings(self, parent_layout: QVBoxLayout) -> None:
        self.tags_group = QGroupBox(t("auto_categorize.settings"))
        tags_layout = QVBoxLayout()

        tags_per_game_layout = QHBoxLayout()
        tags_per_game_layout.addWidget(QLabel(t("auto_categorize.tags_per_game") + ":"))
        self.tags_count_spin = QSpinBox()
        self.tags_count_spin.setMinimum(1)
        self.tags_count_spin.setMaximum(50)
        self.tags_count_spin.setValue(config.TAGS_PER_GAME)
        tags_per_game_layout.addWidget(self.tags_count_spin)
        tags_per_game_layout.addStretch()
        tags_layout.addLayout(tags_per_game_layout)

        self.cb_ignore_common = QCheckBox(t("settings.tags.ignore_common"))
        self.cb_ignore_common.setChecked(config.IGNORE_COMMON_TAGS)
        tags_layout.addWidget(self.cb_ignore_common)

        self.tags_group.setLayout(tags_layout)
        parent_layout.addWidget(self.tags_group)

    def _create_scope_group(self, parent_layout: QVBoxLayout) -> None:
        apply_group = QGroupBox(t("auto_categorize.apply_group"))
        apply_layout = QVBoxLayout()

        self.scope_group = QButtonGroup(self)

        if self._category_name:
            scope_text = t(
                "auto_categorize.scope_category",
                name=self._category_name,
                count=self._games_count,
            )
        else:
            scope_text = t("auto_categorize.scope_selected", count=self._games_count)

        self.rb_selected = QRadioButton(scope_text)
        self.rb_selected.setChecked(True)
        self.scope_group.addButton(self.rb_selected)
        apply_layout.addWidget(self.rb_selected)

        self.rb_all = QRadioButton(t("auto_categorize.scope_all", count=self._all_games_count))
        self.scope_group.addButton(self.rb_all)
        apply_layout.addWidget(self.rb_all)

        if self._games_count == self._all_games_count:
            self.rb_all.setChecked(True)

        apply_group.setLayout(apply_layout)
        parent_layout.addWidget(apply_group)

    def _connect_signals(self) -> None:
        for cb in self._checkboxes.values():
            cb.toggled.connect(self._on_changed)

        self.tags_count_spin.valueChanged.connect(self._on_changed)
        self.rb_selected.toggled.connect(self._on_changed)
        self.rb_all.toggled.connect(self._on_changed)

    def _on_changed(self) -> None:
        self._update_estimate()
        self.methods_changed.emit()

    def _update_estimate(self) -> None:
        if not hasattr(self, "estimate_label") or not hasattr(self, "tags_group"):
            return

        self.tags_group.setVisible(self._checkboxes["tags"].isChecked())

        game_count = self._all_games_count if self.rb_all.isChecked() else self._games_count
        methods = self.get_selected_methods()

        if "tags" in methods:
            seconds = int(game_count * 1.5)
            minutes = seconds // 60
            if minutes > 0:
                time_str = t("auto_categorize.estimate_minutes", count=minutes)
            else:
                time_str = t("auto_categorize.estimate_seconds", count=seconds)
        else:
            time_str = t("auto_categorize.estimate_instant")

        self.estimate_label.setText(
            t("auto_categorize.estimate_label", time=time_str, games=game_count, methods=len(methods))
        )

    def _select_all(self) -> None:
        for cb in self._checkboxes.values():
            cb.setChecked(True)

    def _deselect_all(self) -> None:
        for cb in self._checkboxes.values():
            cb.setChecked(False)

    def get_selected_methods(self) -> list[str]:
        return [key for key, cb in self._checkboxes.items() if cb.isChecked()]

    def get_settings(self) -> dict[str, Any]:
        """Returns scope, methods, tags_count, ignore_common."""
        return {
            "scope": "all" if self.rb_all.isChecked() else "selected",
            "methods": self.get_selected_methods(),
            "tags_count": self.tags_count_spin.value(),
            "ignore_common": self.cb_ignore_common.isChecked(),
        }

    def apply_preset(self, methods: set[str], tags_count: int, ignore_common: bool) -> None:
        for key, cb in self._checkboxes.items():
            cb.setChecked(key in methods)
        self.tags_count_spin.setValue(tags_count)
        self.cb_ignore_common.setChecked(ignore_common)

    def is_curator_selected(self) -> bool:
        cb = self._checkboxes.get("curator")
        return cb.isChecked() if cb else False
