#
# steam_library_manager/services/game_query_service.py
# High-level game query interface over the database layer
#
# Copyright © 2025-2026 SwitchBros
# Licensed under the MIT License. See LICENSE for details.
#

#
# steam_library_manager/services/game_query_service.py
# Read-only query service for game data.
#
# Copyright © 2025-2026 SwitchBros
# Licensed under the MIT License. See LICENSE for details.
#

from __future__ import annotations

import logging

from steam_library_manager.core.game import Game, is_real_game
from steam_library_manager.utils.i18n import t

logger = logging.getLogger("steamlibmgr.game_query")

__all__ = ["GameQueryService"]


class GameQueryService:
    """Stateless query facade over the shared ``games`` dictionary."""

    def __init__(self, games: dict[str, Game], filter_non_games: bool) -> None:
        self._games = games
        self._filter_non_games = filter_non_games

    # Core queries

    def get_real_games(self) -> list[Game]:
        """Returns only real games (excludes Proton/Steam runtime tools)."""
        if self._filter_non_games:
            return [g for g in self._games.values() if is_real_game(g)]
        return list(self._games.values())

    def get_all_games(self) -> list[Game]:
        """Returns ALL games (including tools)."""
        return list(self._games.values())

    def get_games_by_category(self, category: str) -> list[Game]:
        """Gets all games belonging to a specific category."""
        games = [g for g in self.get_real_games() if g.has_category(category)]
        return sorted(games, key=lambda g: g.sort_name.lower())

    def get_uncategorized_games(self, smart_collection_names: set[str] | None = None) -> list[Game]:
        """Gets games that have no user collections (system categories don't count)."""
        # Exclude system collections using all known identifiers (language-independent)
        excluded_categories: set[str] = {
            "favorite",
            "hidden",  # Steam internal IDs
            "Favorites",
            "Favoriten",  # Known display names EN/DE
            "Hidden",
            "Versteckt",
            t("categories.favorites"),  # Current locale
            t("categories.hidden"),
        }
        if smart_collection_names:
            excluded_categories = excluded_categories | smart_collection_names

        uncategorized = []
        for game in self._games.values():
            # Non-game types have their own type categories
            if game.app_type and game.app_type.lower() != "game":
                continue

            # Filter ghost entries and non-games
            if not is_real_game(game):
                continue

            # Only count real Steam collections (not system or smart)
            real_categories = [cat for cat in game.categories if cat not in excluded_categories]

            if not real_categories:
                uncategorized.append(game)

        return sorted(uncategorized, key=lambda g: g.sort_name.lower())

    def get_favorites(self) -> list[Game]:
        """Gets all favorite games."""
        games = [g for g in self.get_real_games() if g.is_favorite()]
        return sorted(games, key=lambda g: g.sort_name.lower())

    def get_all_categories(self) -> dict[str, int]:
        """Gets all categories and their game counts."""
        categories: dict[str, int] = {}
        for game in self.get_real_games():
            for category in game.categories:
                categories[category] = categories.get(category, 0) + 1
        return categories

    def get_game_statistics(self) -> dict[str, int]:
        """Returns game statistics for the status bar."""
        real_games = self.get_real_games()

        games_in_categories: set[str] = set()
        for game in real_games:
            if game.categories:
                games_in_categories.add(game.app_id)

        all_categories = self.get_all_categories()
        category_count = len(all_categories)
        uncategorized = len(real_games) - len(games_in_categories)

        return {
            "total_games": len(real_games),
            "games_in_categories": len(games_in_categories),
            "category_count": category_count,
            "uncategorized_games": uncategorized,
        }
