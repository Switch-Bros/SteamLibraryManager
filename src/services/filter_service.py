# src/services/filter_service.py

"""View-menu filter service for the Steam Library Manager.

Provides FilterState (frozen dataclass) and FilterService which applies
type, platform, and status filters to game lists. Used by the View menu
checkboxes and CategoryPopulator to filter the sidebar tree.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING

from src.services.filter_constants import (
    ALL_ACHIEVEMENT_KEYS,
    ALL_DECK_KEYS,
    ALL_LANGUAGE_KEYS,
    ALL_PEGI_KEYS,
    ALL_PLATFORM_KEYS,
    ALL_SORT_KEYS,
    ALL_STATUS_KEYS,
    ALL_TYPE_KEYS,
    SortKey,
    TYPE_APP_TYPE_MAP,
)

if TYPE_CHECKING:
    from src.core.game import Game

logger = logging.getLogger("steamlibmgr.filter_service")

__all__ = [
    "ALL_ACHIEVEMENT_KEYS",
    "ALL_DECK_KEYS",
    "ALL_LANGUAGE_KEYS",
    "ALL_PEGI_KEYS",
    "ALL_PLATFORM_KEYS",
    "ALL_SORT_KEYS",
    "ALL_STATUS_KEYS",
    "ALL_TYPE_KEYS",
    "FilterService",
    "FilterState",
    "SortKey",
    "TYPE_APP_TYPE_MAP",
]


@dataclass(frozen=True)
class FilterState:
    """Immutable snapshot of the current filter configuration.

    Attributes:
        enabled_types: Type filter keys that are enabled (default: all).
        enabled_platforms: Platform filter keys that are enabled (default: all).
        active_statuses: Status filter keys that are active (default: none).
        active_languages: Language filter keys that are active (default: none = all visible).
        sort_key: Current sort key (default: NAME).
    """

    enabled_types: frozenset[str] = ALL_TYPE_KEYS
    enabled_platforms: frozenset[str] = ALL_PLATFORM_KEYS
    active_statuses: frozenset[str] = frozenset()
    active_languages: frozenset[str] = frozenset()
    active_deck_statuses: frozenset[str] = frozenset()
    active_achievement_filters: frozenset[str] = frozenset()
    active_pegi_ratings: frozenset[str] = frozenset()
    active_curator_ids: frozenset[int] = frozenset()
    sort_key: SortKey = SortKey.NAME


class FilterService:
    """Manages view-menu filter state and applies filters to game lists.

    The service maintains a mutable internal state that tracks which type,
    platform, and status filters are currently enabled. The ``apply()``
    method returns a filtered copy of the input game list.
    """

    def __init__(self) -> None:
        """Initializes the FilterService with default state (all types/platforms on, no status/language)."""
        self._enabled_types: set[str] = set(ALL_TYPE_KEYS)
        self._enabled_platforms: set[str] = set(ALL_PLATFORM_KEYS)
        self._active_statuses: set[str] = set()
        self._active_languages: set[str] = set()
        self._active_deck_statuses: set[str] = set()
        self._active_achievement_filters: set[str] = set()
        self._active_pegi_ratings: set[str] = set()
        self._sort_key: SortKey = SortKey.NAME

        # Curator filter: maps curator_id -> set of recommended app_ids
        self._curator_cache: dict[int, set[int]] = {}
        # Which curator_ids are currently active for filtering
        self._active_curator_ids: set[int] = set()

    @property
    def sort_key(self) -> SortKey:
        """The current sort key."""
        return self._sort_key

    @property
    def curator_cache(self) -> dict[int, set[int]]:
        """The current curator recommendation cache."""
        return self._curator_cache

    @property
    def state(self) -> FilterState:
        """Returns the current filter state as a frozen snapshot."""
        return FilterState(
            enabled_types=frozenset(self._enabled_types),
            enabled_platforms=frozenset(self._enabled_platforms),
            active_statuses=frozenset(self._active_statuses),
            active_languages=frozenset(self._active_languages),
            active_deck_statuses=frozenset(self._active_deck_statuses),
            active_achievement_filters=frozenset(self._active_achievement_filters),
            active_pegi_ratings=frozenset(self._active_pegi_ratings),
            active_curator_ids=frozenset(self._active_curator_ids),
            sort_key=self._sort_key,
        )

    def restore_state(self, state: FilterState) -> None:
        """Replaces the current filter state with the given snapshot.

        Args:
            state: A frozen FilterState to restore from.
        """
        self._enabled_types = set(state.enabled_types)
        self._enabled_platforms = set(state.enabled_platforms)
        self._active_statuses = set(state.active_statuses)
        self._active_languages = set(state.active_languages)
        self._active_deck_statuses = set(state.active_deck_statuses)
        self._active_achievement_filters = set(state.active_achievement_filters)
        self._active_pegi_ratings = set(state.active_pegi_ratings)
        self._active_curator_ids = set(state.active_curator_ids)
        self._sort_key = state.sort_key

    def set_sort_key(self, key: str) -> None:
        """Sets the sort key from a string value.

        Args:
            key: One of "name", "playtime", "last_played", "release_date".
        """
        try:
            self._sort_key = SortKey(key)
        except ValueError:
            logger.warning("Unknown sort key: %s, falling back to NAME", key)
            self._sort_key = SortKey.NAME

    def sort_games(self, games: list[Game]) -> list[Game]:
        """Sorts a list of games according to the current sort key.

        Args:
            games: The games to sort.

        Returns:
            A new sorted list of games.
        """
        if self._sort_key == SortKey.PLAYTIME:
            return sorted(games, key=lambda g: g.playtime_minutes, reverse=True)
        if self._sort_key == SortKey.LAST_PLAYED:
            # Games without last_played go to the end
            return sorted(
                games,
                key=lambda g: (g.last_played is not None, g.last_played or ""),
                reverse=True,
            )
        if self._sort_key == SortKey.RELEASE_DATE:
            # Games without release_year go to the end
            return sorted(
                games,
                key=lambda g: g.release_year if g.release_year else "",
                reverse=True,
            )
        # Default: NAME (A-Z) using sort_name
        return sorted(games, key=lambda g: g.sort_name.lower())

    def _toggle_filter(
        self, key: str, active: bool, valid_keys: frozenset[str], target_set: set[str], label: str
    ) -> None:
        """Toggles a single filter key in the target set.

        Args:
            key: The filter key to toggle.
            active: Whether to add (True) or remove (False).
            valid_keys: Set of valid keys for validation.
            target_set: The mutable set to modify.
            label: Category label for log messages.
        """
        if key not in valid_keys:
            logger.warning("Unknown %s filter key: %s", label, key)
            return
        target_set.add(key) if active else target_set.discard(key)

    def toggle_type(self, key: str, enabled: bool) -> None:
        """Enables or disables a type filter."""
        self._toggle_filter(key, enabled, ALL_TYPE_KEYS, self._enabled_types, "type")

    def toggle_platform(self, key: str, enabled: bool) -> None:
        """Enables or disables a platform filter."""
        self._toggle_filter(key, enabled, ALL_PLATFORM_KEYS, self._enabled_platforms, "platform")

    def toggle_status(self, key: str, active: bool) -> None:
        """Activates or deactivates a status filter."""
        self._toggle_filter(key, active, ALL_STATUS_KEYS, self._active_statuses, "status")

    def toggle_language(self, key: str, active: bool) -> None:
        """Activates or deactivates a language filter."""
        self._toggle_filter(key, active, ALL_LANGUAGE_KEYS, self._active_languages, "language")

    def toggle_deck_status(self, key: str, active: bool) -> None:
        """Activates or deactivates a Steam Deck compatibility filter."""
        self._toggle_filter(key, active, ALL_DECK_KEYS, self._active_deck_statuses, "deck status")

    def toggle_pegi_rating(self, key: str, active: bool) -> None:
        """Activates or deactivates a PEGI age rating filter."""
        self._toggle_filter(key, active, ALL_PEGI_KEYS, self._active_pegi_ratings, "PEGI")

    def toggle_achievement_filter(self, key: str, active: bool) -> None:
        """Activates or deactivates an achievement filter."""
        self._toggle_filter(key, active, ALL_ACHIEVEMENT_KEYS, self._active_achievement_filters, "achievement")

    def set_curator_cache(self, cache: dict[int, set[int]]) -> None:
        """Replaces the curator recommendation cache.

        Args:
            cache: Maps curator_id to the set of recommended app_ids.
        """
        self._curator_cache = cache

    def toggle_curator_filter(self, curator_id: int, active: bool) -> None:
        """Activates or deactivates a curator filter.

        Args:
            curator_id: The curator ID to toggle.
            active: Whether to enable (True) or disable (False).
        """
        if curator_id not in self._curator_cache:
            logger.warning("Unknown curator ID for filter: %d", curator_id)
            return
        self._active_curator_ids.add(curator_id) if active else self._active_curator_ids.discard(curator_id)

    def is_type_category_visible(self, type_key: str) -> bool:
        """Checks whether a type category should be shown in the sidebar.

        Args:
            type_key: One of "soundtracks", "tools", "software", "videos".

        Returns:
            True if the corresponding type filter is enabled.
        """
        return type_key in self._enabled_types

    def has_active_filters(self) -> bool:
        """Checks whether any filter deviates from the default state.

        Returns:
            True if any type/platform is disabled or any status/language is active.
        """
        if self._enabled_types != ALL_TYPE_KEYS:
            return True
        if self._enabled_platforms != ALL_PLATFORM_KEYS:
            return True
        if self._active_statuses:
            return True
        if self._active_languages:
            return True
        if self._active_deck_statuses:
            return True
        if self._active_achievement_filters:
            return True
        if self._active_pegi_ratings:
            return True
        if self._active_curator_ids:
            return True
        return False

    def apply(self, games: list[Game]) -> list[Game]:
        """Applies all active filters to a list of games.

        Filter pipeline:
        1. Type filter: game.app_type must match an enabled type.
        2. Platform filter: game must have at least one enabled platform,
           or have no platform data (safe default).
        3. Status filter (OR): if any status is active, game must match
           at least one active status.

        Args:
            games: The input game list.

        Returns:
            A new list containing only games that pass all filters.
        """
        if not self.has_active_filters():
            return games

        result: list[Game] = []
        for game in games:
            if not self._passes_type_filter(game):
                continue
            if not self._passes_platform_filter(game):
                continue
            if not self._passes_status_filter(game):
                continue
            if not self._passes_language_filter(game):
                continue
            if not self._passes_deck_filter(game):
                continue
            if not self._passes_achievement_filter(game):
                continue
            if not self._passes_pegi_filter(game):
                continue
            if not self._passes_curator_filter(game):
                continue
            result.append(game)
        return result

    def _passes_type_filter(self, game: Game) -> bool:
        """Checks if a game passes the type filter.

        Args:
            game: The game to check.

        Returns:
            True if the game's app_type matches any enabled type key.
        """
        if self._enabled_types == ALL_TYPE_KEYS:
            return True

        app_type = game.app_type.lower() if game.app_type else ""
        for type_key in self._enabled_types:
            accepted_types = TYPE_APP_TYPE_MAP.get(type_key, frozenset())
            if app_type in accepted_types:
                return True
        return False

    def _passes_platform_filter(self, game: Game) -> bool:
        """Checks if a game passes the platform filter.

        Games without platform data always pass (safe default).

        Args:
            game: The game to check.

        Returns:
            True if the game has at least one enabled platform or no data.
        """
        if self._enabled_platforms == ALL_PLATFORM_KEYS:
            return True

        if not game.platforms:
            return True

        platforms_lower = {p.lower() for p in game.platforms}
        for platform_key in self._enabled_platforms:
            if platform_key in platforms_lower:
                return True
        return False

    def _passes_status_filter(self, game: Game) -> bool:
        """Checks if a game passes the status filter (OR logic).

        If no status filters are active, all games pass.

        Args:
            game: The game to check.

        Returns:
            True if no status is active or game matches at least one.
        """
        if not self._active_statuses:
            return True

        for status_key in self._active_statuses:
            if status_key == "installed" and game.installed:
                return True
            if status_key == "not_installed" and not game.installed:
                return True
            if status_key == "hidden" and game.hidden:
                return True
            if status_key == "with_playtime" and game.playtime_minutes > 0:
                return True
            if status_key == "favorites" and game.is_favorite():
                return True
        return False

    def _passes_language_filter(self, game: Game) -> bool:
        """Checks if a game passes the language filter (OR logic).

        If no language filters are active, all games pass. Games without
        language data always pass (safe default).

        Args:
            game: The game to check.

        Returns:
            True if no language is active, game has no language data,
            or game supports at least one active language.
        """
        if not self._active_languages:
            return True

        if not game.languages:
            return True

        game_langs_lower = {lang.lower().replace(" ", "_") for lang in game.languages}
        return bool(game_langs_lower & self._active_languages)

    def _passes_deck_filter(self, game: Game) -> bool:
        """Checks if a game passes the Steam Deck compatibility filter (OR logic).

        If no deck status filters are active, all games pass. Games without
        deck status data are treated as "unknown".

        Args:
            game: The game to check.

        Returns:
            True if no deck filter is active or game matches at least one.
        """
        if not self._active_deck_statuses:
            return True

        status = game.steam_deck_status.lower() if game.steam_deck_status else "unknown"
        return status in self._active_deck_statuses

    def _passes_achievement_filter(self, game: Game) -> bool:
        """Checks if a game passes the achievement filter (OR logic).

        If no achievement filters are active, all games pass.

        Args:
            game: The game to check.

        Returns:
            True if no filter is active or game matches at least one.
        """
        if not self._active_achievement_filters:
            return True

        pct = game.achievement_percentage
        total = game.achievement_total

        for key in self._active_achievement_filters:
            if key == "perfect" and game.achievement_perfect:
                return True
            if key == "almost" and 75 <= pct < 100:
                return True
            if key == "progress" and 25 <= pct < 75:
                return True
            if key == "started" and 0 < pct < 25:
                return True
            if key == "none" and total == 0:
                return True
        return False

    def _passes_pegi_filter(self, game: Game) -> bool:
        """Checks if a game passes the PEGI age rating filter (OR logic).

        If no PEGI filters are active, all games pass. Games without
        PEGI data match the "pegi_none" key.

        Args:
            game: The game to check.

        Returns:
            True if no PEGI filter is active or game matches at least one.
        """
        if not self._active_pegi_ratings:
            return True

        pegi_map = {
            "pegi_3": "3",
            "pegi_7": "7",
            "pegi_12": "12",
            "pegi_16": "16",
            "pegi_18": "18",
        }
        rating = game.pegi_rating or ""

        if not rating:
            return "pegi_none" in self._active_pegi_ratings

        allowed = {pegi_map[k] for k in self._active_pegi_ratings if k in pegi_map}
        return rating in allowed

    def _passes_curator_filter(self, game: Game) -> bool:
        """Checks if a game passes the curator filter (OR logic).

        If no curator filters are active, all games pass. When active,
        a game must be recommended by at least one of the selected curators.
        Uses the in-memory cache — no database access.

        Args:
            game: The game to check.

        Returns:
            True if no curator filter is active or game matches at least one.
        """
        if not self._active_curator_ids:
            return True

        try:
            numeric_id = int(game.app_id)
        except (ValueError, TypeError):
            return False

        for curator_id in self._active_curator_ids:
            recommended = self._curator_cache.get(curator_id, set())
            if numeric_id in recommended:
                return True
        return False
