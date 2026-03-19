#
# steam_library_manager/ui/handlers/category_change_handler.py
# Category rename, delete, reorder from UI events
#
# Copyright © 2025-2026 SwitchBros
# Licensed under the MIT License. See LICENSE for details.
#

from __future__ import annotations

from PyQt6.QtCore import QTimer

from steam_library_manager.ui.handlers.empty_collection_handler import EmptyCollectionHandler

__all__ = ["CategoryChangeHandler"]


class CategoryChangeHandler:
    """Handles category changes from checkboxes and drag-drop.

    Supports single and multi-select, batches rapid events
    to avoid excessive UI refreshes.
    """

    def __init__(self, main_window):
        self.mw = main_window
        self.empty_handler = EmptyCollectionHandler(main_window)

    def apply_category_to_games(self, games, category, checked):
        # add or remove category from games
        if not self.mw.category_service:
            return

        for g in games:
            if checked:
                if category not in g.categories:
                    g.categories.append(category)
                    self.mw.category_service.add_app_to_category(g.app_id, category)
            else:
                if category in g.categories:
                    g.categories.remove(category)
                    self.mw.category_service.remove_app_from_category(g.app_id, category)
                    self.empty_handler.check_and_delete_if_empty(category)

    def on_category_changed_from_details(self, app_id, category, checked):
        # checkbox toggle from details widget
        if not self.mw.cloud_storage_parser:
            return

        # batch mode - just update data
        if hasattr(self.mw, "in_batch_update") and self.mw.in_batch_update:
            targets = []
            if len(self.mw.selected_games) > 1:
                targets = self.mw.selected_games
            else:
                g = self.mw.game_manager.get_game(app_id)
                if g:
                    targets = [g]
            self.apply_category_to_games(targets, category, checked)
            return

        self.mw.in_batch_update = True

        # determine which games to update
        targets = []
        if len(self.mw.selected_games) > 1:
            targets = self.mw.selected_games
        else:
            g = self.mw.game_manager.get_game(app_id)
            if g:
                targets = [g]

        if not targets:
            return

        self.apply_category_to_games(targets, category, checked)

        # noinspection PyProtectedMember
        self.mw._schedule_save()

        sel_ids = [g.app_id for g in self.mw.selected_games]

        # maintain search if active
        if self.mw.current_search_query:
            self.mw.view_actions.on_search(self.mw.current_search_query)
        else:
            self.mw.populate_categories()

        if sel_ids:
            self.mw.selection_handler.restore_game_selection(sel_ids)

        all_cats = list(self.mw.game_manager.get_all_categories().keys())

        # refresh details
        if len(self.mw.selected_games) > 1:
            self.mw.details_widget.set_games(self.mw.selected_games, all_cats)
        elif len(self.mw.selected_games) == 1:
            self.mw.details_widget.set_game(self.mw.selected_games[0], all_cats)

        # reset batch flag after 500ms
        QTimer.singleShot(500, lambda: setattr(self.mw, "in_batch_update", False))

    def on_games_dropped(self, games, target_category):
        # drag-drop onto category
        if not self.mw.cloud_storage_parser or not self.mw.category_service:
            return

        for g in games:
            if target_category not in g.categories:
                g.categories.append(target_category)
                self.mw.category_service.add_app_to_category(g.app_id, target_category)

        self.mw.save_collections()

        if self.mw.current_search_query:
            self.mw.view_actions.on_search(self.mw.current_search_query)
        else:
            self.mw.populate_categories()

        # refresh details if dropped game is selected
        if games and self.mw.details_widget.current_game:
            dropped_ids = [g.app_id for g in games]
            if self.mw.details_widget.current_game.app_id in dropped_ids:
                all_cats = list(self.mw.game_manager.get_all_categories().keys())
                self.mw.details_widget.set_game(self.mw.details_widget.current_game, all_cats)
