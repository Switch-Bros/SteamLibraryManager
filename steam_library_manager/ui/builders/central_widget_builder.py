#
# steam_library_manager/ui/builders/central_widget_builder.py
# Builds the central widget layout with game tree and details panel
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
        # create central widget with search, tree, and details panel
        central = QWidget()
        self.mw.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(5, 5, 5, 5)

        # TODO: responsive splitter sizes?
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # LEFT SIDE
        left = QWidget()
        llayout = QVBoxLayout(left)
        llayout.setContentsMargins(0, 0, 0, 0)
        llayout.setSpacing(2)

        # Search Bar
        slayout = QHBoxLayout()
        slayout.addWidget(QLabel(t("emoji.search")))
        search = QLineEdit()
        search.setPlaceholderText(t("ui.main_window.search_placeholder"))
        # noinspection PyUnresolvedReferences
        search.textChanged.connect(self.mw.view_actions.on_search)
        slayout.addWidget(search)

        clear_btn = QPushButton(t("emoji.clear"))
        # noinspection PyUnresolvedReferences
        clear_btn.clicked.connect(self.mw.view_actions.clear_search)
        clear_btn.setMaximumWidth(30)
        slayout.addWidget(clear_btn)
        llayout.addLayout(slayout)

        # Tree Controls
        blayout = QHBoxLayout()
        exp_btn = QPushButton("▼ %s" % t("menu.edit.collections.expand_all"))
        # noinspection PyUnresolvedReferences
        exp_btn.clicked.connect(self.mw.view_actions.expand_all)
        blayout.addWidget(exp_btn)

        col_btn = QPushButton("▲ %s" % t("menu.edit.collections.collapse_all"))
        # noinspection PyUnresolvedReferences
        col_btn.clicked.connect(self.mw.view_actions.collapse_all)
        blayout.addWidget(col_btn)
        llayout.addLayout(blayout)

        # Inline Progress Area (hidden by default)
        load_lbl = QLabel()
        load_lbl.setVisible(False)
        llayout.addWidget(load_lbl)

        pbar = QProgressBar()
        pbar.setMaximumHeight(8)
        pbar.setTextVisible(False)
        pbar.setVisible(False)
        llayout.addWidget(pbar)

        # Tree Widget
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
        llayout.addWidget(tree)

        splitter.addWidget(left)

        # RIGHT SIDE (Details)
        details = GameDetailsWidget()
        # noinspection PyUnresolvedReferences
        details.category_changed.connect(self.mw.category_change_handler.on_category_changed_from_details)
        # noinspection PyUnresolvedReferences
        details.edit_metadata.connect(self.mw.metadata_actions.edit_game_metadata)
        # noinspection PyUnresolvedReferences
        details.pegi_override_requested.connect(self.mw.metadata_actions.on_pegi_override_requested)
        splitter.addWidget(details)

        splitter.setSizes([350, 1050])
        layout.addWidget(splitter)

        return {
            "tree": tree,
            "details_widget": details,
            "search_entry": search,
            "loading_label": load_lbl,
            "progress_bar": pbar,
        }
