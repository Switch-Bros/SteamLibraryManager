#
# steam_library_manager/ui/handlers/category_change_handler.py
# Handler for category change operations (toggle, drag/drop).
#
# Copyright © 2025-2026 SwitchBros
# Licensed under the MIT License. See LICENSE for details.
#

from __future__ import annotations
from typing import TYPE_CHECKING

from PyQt6.QtCore import QTimer

from steam_library_manager.core.game_manager import Game
from steam_library_manager.ui.handlers.empty_collection_handler import EmptyCollectionHandler

if TYPE_CHECKING:
    from steam_library_manager.ui.main_window import MainWindow

__all__ = ["CategoryChangeHandler"]


class CategoryChangeHandler:
    """Handles category assignment changes from UI events."""

    def __init__(self, main_window: "MainWindow") -> None:
        self.mw: "MainWindow" = main_window
        self.empty_handler = EmptyCollectionHandler(main_window)

    def apply_category_to_games(self, games: list[Game], category: str, checked: bool) -> None:
        """Apply category add/remove to a list of games."""
        if not self.mw.category_service:
            return

        for game in games:
            if checked:
                if category not in game.categories:
                    game.categories.append(category)
                    self.mw.category_service.add_app_to_category(game.app_id, category)
            else:
                if category in game.categories:
                    game.categories.remove(category)
                    self.mw.category_service.remove_app_from_category(game.app_id, category)

                    self.empty_handler.check_and_delete_if_empty(category)

    def on_category_changed_from_details(self, app_id: str, category: str, checked: bool) -> None:
        """Handles category toggle from details widget (single or multi-select)."""
        if not self.mw.cloud_storage_parser:
            return

        if hasattr(self.mw, "in_batch_update") and self.mw.in_batch_update:
            games_to_update = []
            if len(self.mw.selected_games) > 1:
                games_to_update = self.mw.selected_games
            else:
                game = self.mw.game_manager.get_game(app_id)
                if game:
                    games_to_update = [game]

            self.apply_category_to_games(games_to_update, category, checked)
            return

        self.mw.in_batch_update = True
        games_to_update = []
        if len(self.mw.selected_games) > 1:
            games_to_update = self.mw.selected_games
        else:
            game = self.mw.game_manager.get_game(app_id)
            if game:
                games_to_update = [game]

        if not games_to_update:
            return

        self.apply_category_to_games(games_to_update, category, checked)

        # noinspection PyProtectedMember
        self.mw._schedule_save()

        selected_app_ids = [game.app_id for game in self.mw.selected_games]

        if self.mw.current_search_query:
            self.mw.view_actions.on_search(self.mw.current_search_query)
        else:
            self.mw.populate_categories()

        if selected_app_ids:
            self.mw.selection_handler.restore_game_selection(selected_app_ids)

        all_categories = list(self.mw.game_manager.get_all_categories().keys())

        if len(self.mw.selected_games) > 1:
            self.mw.details_widget.set_games(self.mw.selected_games, all_categories)
        elif len(self.mw.selected_games) == 1:
            self.mw.details_widget.set_game(self.mw.selected_games[0], all_categories)

        QTimer.singleShot(500, lambda: setattr(self.mw, "in_batch_update", False))

    def on_games_dropped(self, games: list[Game], target_category: str) -> None:
        """Handles drag-and-drop of games onto a category."""
        if not self.mw.cloud_storage_parser or not self.mw.category_service:
            return

        for game in games:
            if target_category not in game.categories:
                game.categories.append(target_category)
                self.mw.category_service.add_app_to_category(game.app_id, target_category)

        self.mw.save_collections()

        if self.mw.current_search_query:
            self.mw.view_actions.on_search(self.mw.current_search_query)
        else:
            self.mw.populate_categories()

        if games and self.mw.details_widget.current_game:
            dropped_app_ids = [g.app_id for g in games]
            if self.mw.details_widget.current_game.app_id in dropped_app_ids:
                all_categories = list(self.mw.game_manager.get_all_categories().keys())
                self.mw.details_widget.set_game(self.mw.details_widget.current_game, all_categories)
