#
# steam_library_manager/ui/handlers/empty_collection_handler.py
# Automatic deletion of empty collections after game removal.
#
# Copyright © 2025-2026 SwitchBros
# Licensed under the MIT License. See LICENSE for details.
#

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from steam_library_manager.ui.main_window import MainWindow

__all__ = ["EmptyCollectionHandler"]


class EmptyCollectionHandler:
    """Handles automatic deletion of empty user collections."""

    def __init__(self, main_window: "MainWindow") -> None:
        self.mw: "MainWindow" = main_window

    def check_and_delete_if_empty(self, category_name: str) -> bool:
        """Delete collection if empty. Returns True if deleted."""
        from steam_library_manager.ui.constants import get_protected_collection_names

        if category_name in get_protected_collection_names():
            return False

        if not self.mw.game_manager or not self.mw.category_service:
            return False

        games_in_category = self.mw.game_manager.get_games_by_category(category_name)

        if len(games_in_category) == 0:
            self.mw.category_service.delete_category(category_name)
            return True

        return False
