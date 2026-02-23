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
        self._sort_key: SortKey = SortKey.NAME

    @property
    def sort_key(self) -> SortKey:
        """The current sort key."""
        return self._sort_key

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

    def toggle_type(self, key: str, enabled: bool) -> None:
        """Enables or disables a type filter.

        Args:
            key: The type key (e.g. "games", "soundtracks").
            enabled: True to show this type, False to hide it.
        """
        if key not in ALL_TYPE_KEYS:
            logger.warning("Unknown type filter key: %s", key)
            return
        if enabled:
            self._enabled_types.add(key)
        else:
            self._enabled_types.discard(key)

    def toggle_platform(self, key: str, enabled: bool) -> None:
        """Enables or disables a platform filter.

        Args:
            key: The platform key (e.g. "linux", "windows", "steamos").
            enabled: True to show this platform, False to hide it.
        """
        if key not in ALL_PLATFORM_KEYS:
            logger.warning("Unknown platform filter key: %s", key)
            return
        if enabled:
            self._enabled_platforms.add(key)
        else:
            self._enabled_platforms.discard(key)

    def toggle_status(self, key: str, active: bool) -> None:
        """Activates or deactivates a status filter.

        When at least one status filter is active, only games matching
        any active status are shown (OR logic).

        Args:
            key: The status key (e.g. "installed", "favorites").
            active: True to activate, False to deactivate.
        """
        if key not in ALL_STATUS_KEYS:
            logger.warning("Unknown status filter key: %s", key)
            return
        if active:
            self._active_statuses.add(key)
        else:
            self._active_statuses.discard(key)

    def toggle_language(self, key: str, active: bool) -> None:
        """Activates or deactivates a language filter.

        When at least one language filter is active, only games supporting
        any active language are shown (OR logic). When none are active,
        all games pass (no language filtering).

        Args:
            key: The language key (e.g. "english", "german").
            active: True to activate, False to deactivate.
        """
        if key not in ALL_LANGUAGE_KEYS:
            logger.warning("Unknown language filter key: %s", key)
            return
        if active:
            self._active_languages.add(key)
        else:
            self._active_languages.discard(key)

    def toggle_deck_status(self, key: str, active: bool) -> None:
        """Activates or deactivates a Steam Deck compatibility filter.

        When at least one deck status filter is active, only games matching
        any active status are shown (OR logic). When none are active,
        all games pass (no deck filtering).

        Args:
            key: The deck status key (e.g. "verified", "playable").
            active: True to activate, False to deactivate.
        """
        if key not in ALL_DECK_KEYS:
            logger.warning("Unknown deck status filter key: %s", key)
            return
        if active:
            self._active_deck_statuses.add(key)
        else:
            self._active_deck_statuses.discard(key)

    def toggle_achievement_filter(self, key: str, active: bool) -> None:
        """Activates or deactivates an achievement filter.

        When at least one achievement filter is active, only games matching
        any active filter are shown (OR logic). When none are active,
        all games pass (no achievement filtering).

        Args:
            key: The achievement filter key (e.g. "perfect", "almost").
            active: True to activate, False to deactivate.
        """
        if key not in ALL_ACHIEVEMENT_KEYS:
            logger.warning("Unknown achievement filter key: %s", key)
            return
        if active:
            self._active_achievement_filters.add(key)
        else:
            self._active_achievement_filters.discard(key)

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
