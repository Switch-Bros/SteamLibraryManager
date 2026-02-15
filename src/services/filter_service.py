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

if TYPE_CHECKING:
    from src.core.game import Game

logger = logging.getLogger("steamlibmgr.filter_service")

__all__ = ["FilterService", "FilterState"]

# All known type keys with their matching app_type values
ALL_TYPE_KEYS: frozenset[str] = frozenset({"games", "soundtracks", "software", "videos", "dlcs", "tools"})

# All known platform keys
ALL_PLATFORM_KEYS: frozenset[str] = frozenset({"linux", "windows", "steamos"})

# All known status keys
ALL_STATUS_KEYS: frozenset[str] = frozenset({"installed", "not_installed", "hidden", "with_playtime", "favorites"})

# Maps menu type keys to the app_type values they accept
_TYPE_APP_TYPE_MAP: dict[str, frozenset[str]] = {
    "games": frozenset({"game", ""}),
    "soundtracks": frozenset({"music"}),
    "software": frozenset({"application"}),
    "videos": frozenset({"video"}),
    "dlcs": frozenset({"dlc"}),
    "tools": frozenset({"tool"}),
}


@dataclass(frozen=True)
class FilterState:
    """Immutable snapshot of the current filter configuration.

    Attributes:
        enabled_types: Type filter keys that are enabled (default: all).
        enabled_platforms: Platform filter keys that are enabled (default: all).
        active_statuses: Status filter keys that are active (default: none).
    """

    enabled_types: frozenset[str] = ALL_TYPE_KEYS
    enabled_platforms: frozenset[str] = ALL_PLATFORM_KEYS
    active_statuses: frozenset[str] = frozenset()


class FilterService:
    """Manages view-menu filter state and applies filters to game lists.

    The service maintains a mutable internal state that tracks which type,
    platform, and status filters are currently enabled. The ``apply()``
    method returns a filtered copy of the input game list.
    """

    def __init__(self) -> None:
        """Initializes the FilterService with default state (all types/platforms on, no status)."""
        self._enabled_types: set[str] = set(ALL_TYPE_KEYS)
        self._enabled_platforms: set[str] = set(ALL_PLATFORM_KEYS)
        self._active_statuses: set[str] = set()

    @property
    def state(self) -> FilterState:
        """Returns the current filter state as a frozen snapshot."""
        return FilterState(
            enabled_types=frozenset(self._enabled_types),
            enabled_platforms=frozenset(self._enabled_platforms),
            active_statuses=frozenset(self._active_statuses),
        )

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
            True if any type/platform is disabled or any status is active.
        """
        if self._enabled_types != ALL_TYPE_KEYS:
            return True
        if self._enabled_platforms != ALL_PLATFORM_KEYS:
            return True
        if self._active_statuses:
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
            accepted_types = _TYPE_APP_TYPE_MAP.get(type_key, frozenset())
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
