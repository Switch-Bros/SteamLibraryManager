#
# steam_library_manager/ui/builders/central_widget_builder.py
# Builds the main splitter layout with game tree and details panel
#
# Copyright © 2025-2026 SwitchBros
# Licensed under the MIT License. See LICENSE for details.
#

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton, QLabel, QSplitter, QProgressBar

from steam_library_manager.ui.widgets.category_tree import GameTreeWidget
from steam_library_manager.ui.widgets.game_details_widget import GameDetailsWidget
from steam_library_manager.utils.i18n import t

if TYPE_CHECKING:
    from steam_library_manager.ui.main_window import MainWindow

__all__ = ["CentralWidgetBuilder"]


class CentralWidgetBuilder:
    """Builds the central widget with splitter layout."""

    def __init__(self, main_window: "MainWindow"):

        self.mw = main_window

    def build(self) -> dict[str, Any]:
        """Builds the central widget and returns references to key widgets."""
        central = QWidget()
        self.mw.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(5, 5, 5, 5)

        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Left side
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(2)

        search_layout = QHBoxLayout()
        search_layout.addWidget(QLabel(t("emoji.search")))
        search_entry = QLineEdit()
        search_entry.setPlaceholderText(t("ui.main_window.search_placeholder"))
        # noinspection PyUnresolvedReferences
        search_entry.textChanged.connect(self.mw.view_actions.on_search)
        search_layout.addWidget(search_entry)

        clear_btn = QPushButton(t("emoji.clear"))
        # noinspection PyUnresolvedReferences
        clear_btn.clicked.connect(self.mw.view_actions.clear_search)
        clear_btn.setMaximumWidth(30)
        search_layout.addWidget(clear_btn)
        left_layout.addLayout(search_layout)

        btn_layout = QHBoxLayout()
        expand_btn = QPushButton(f"▼ {t('menu.edit.collections.expand_all')}")
        # noinspection PyUnresolvedReferences
        expand_btn.clicked.connect(self.mw.view_actions.expand_all)
        btn_layout.addWidget(expand_btn)

        collapse_btn = QPushButton(f"▲ {t('menu.edit.collections.collapse_all')}")
        # noinspection PyUnresolvedReferences
        collapse_btn.clicked.connect(self.mw.view_actions.collapse_all)
        btn_layout.addWidget(collapse_btn)
        left_layout.addLayout(btn_layout)

        loading_label = QLabel()
        loading_label.setVisible(False)
        left_layout.addWidget(loading_label)

        progress_bar = QProgressBar()
        progress_bar.setMaximumHeight(8)
        progress_bar.setTextVisible(False)
        progress_bar.setVisible(False)
        left_layout.addWidget(progress_bar)

        tree = GameTreeWidget()
        # noinspection PyUnresolvedReferences,DuplicatedCode
        tree.game_clicked.connect(self.mw.selection_handler.on_game_selected)
        # noinspection PyUnresolvedReferences
        tree.game_right_clicked.connect(self.mw.on_game_right_click)
        # noinspection PyUnresolvedReferences
        tree.category_right_clicked.connect(self.mw.on_category_right_click)
        # noinspection PyUnresolvedReferences
        tree.selection_changed.connect(self.mw.selection_handler.on_games_selected)
        # noinspection PyUnresolvedReferences
        tree.games_dropped.connect(self.mw.category_change_handler.on_games_dropped)
        left_layout.addWidget(tree)

        splitter.addWidget(left_widget)

        # Right side
        details_widget = GameDetailsWidget()
        # noinspection PyUnresolvedReferences
        details_widget.category_changed.connect(self.mw.category_change_handler.on_category_changed_from_details)
        # noinspection PyUnresolvedReferences
        details_widget.edit_metadata.connect(self.mw.metadata_actions.edit_game_metadata)
        # noinspection PyUnresolvedReferences
        details_widget.pegi_override_requested.connect(self.mw.metadata_actions.on_pegi_override_requested)
        splitter.addWidget(details_widget)

        splitter.setSizes([350, 1050])
        layout.addWidget(splitter)

        return {
            "tree": tree,
            "details_widget": details_widget,
            "search_entry": search_entry,
            "loading_label": loading_label,
            "progress_bar": progress_bar,
        }
