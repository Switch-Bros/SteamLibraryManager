"""
Builder for the central widget layout.

This module contains the CentralWidgetBuilder that constructs the main
application layout with splitter, game tree, and details panel.
"""

from __future__ import annotations
from typing import TYPE_CHECKING, Any

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton, QLabel, QSplitter
from PyQt6.QtCore import Qt

from src.ui.widgets.game_details_widget import GameDetailsWidget
from src.ui.widgets.category_tree import GameTreeWidget
from src.utils.i18n import t

if TYPE_CHECKING:
    from src.ui.main_window import MainWindow


class CentralWidgetBuilder:
    """Builder for the central widget with splitter layout.

    Constructs the main application view including:
    - Left sidebar with search and game tree
    - Right panel with game details
    - Expand/collapse controls

    Attributes:
        mw: Reference to the MainWindow instance.
    """

    def __init__(self, main_window: "MainWindow"):
        """Initialize the builder.

        Args:
            main_window: The MainWindow instance.
        """
        self.mw = main_window

    def build(self) -> dict[str, Any]:
        """Build the central widget layout.

        Creates the complete central widget with:
        - Search bar
        - Expand/collapse buttons
        - Game tree widget
        - Game details panel

        Returns:
            dict containing references to created widgets:
            - 'tree': GameTreeWidget
            - 'details_widget': GameDetailsWidget
            - 'search_entry': QLineEdit
        """
        # Central Widget
        central = QWidget()
        self.mw.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(5, 5, 5, 5)

        splitter = QSplitter(Qt.Orientation.Horizontal)

        # LEFT SIDE
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(2)

        # Search Bar
        search_layout = QHBoxLayout()
        search_layout.addWidget(QLabel(t("ui.main_window.search_icon")))
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

        # Tree Controls
        btn_layout = QHBoxLayout()
        expand_btn = QPushButton(f"▼ {t('ui.menu.view.expand_all')}")
        # noinspection PyUnresolvedReferences
        expand_btn.clicked.connect(self.mw.view_actions.expand_all)
        btn_layout.addWidget(expand_btn)

        collapse_btn = QPushButton(f"▲ {t('ui.menu.view.collapse_all')}")
        # noinspection PyUnresolvedReferences
        collapse_btn.clicked.connect(self.mw.view_actions.collapse_all)
        btn_layout.addWidget(collapse_btn)
        left_layout.addLayout(btn_layout)

        # Tree Widget
        tree = GameTreeWidget()
        # noinspection PyUnresolvedReferences,DuplicatedCode
        tree.game_clicked.connect(self.mw.on_game_selected)
        # noinspection PyUnresolvedReferences
        tree.game_right_clicked.connect(self.mw.on_game_right_click)
        # noinspection PyUnresolvedReferences
        tree.category_right_clicked.connect(self.mw.on_category_right_click)
        # noinspection PyUnresolvedReferences
        tree.selection_changed.connect(self.mw.on_games_selected)
        # noinspection PyUnresolvedReferences
        tree.games_dropped.connect(self.mw.on_games_dropped)
        left_layout.addWidget(tree)

        splitter.addWidget(left_widget)

        # RIGHT SIDE (Details)
        details_widget = GameDetailsWidget()
        # noinspection PyUnresolvedReferences
        details_widget.category_changed.connect(self.mw.on_category_changed_from_details)
        # noinspection PyUnresolvedReferences
        details_widget.edit_metadata.connect(self.mw.edit_actions.edit_game_metadata)
        # noinspection PyUnresolvedReferences
        details_widget.pegi_override_requested.connect(self.mw.edit_actions.on_pegi_override_requested)
        splitter.addWidget(details_widget)

        splitter.setSizes([350, 1050])
        layout.addWidget(splitter)

        return {"tree": tree, "details_widget": details_widget, "search_entry": search_entry}
