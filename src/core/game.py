# src/core/game.py

"""Game dataclass and filtering constants for the Steam Library Manager.

This module defines the central Game dataclass used by 15+ modules across
the codebase, along with constants and helpers for filtering non-game
Steam apps (Proton, Steam Runtime, etc.).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime

from src.utils.i18n import t

__all__ = [
    "Game",
    "NON_GAME_APP_IDS",
    "NON_GAME_APP_TYPES",
    "NON_GAME_NAME_PATTERNS",
    "is_real_game",
]


@dataclass
class Game:
    """Represents a single Steam game with all its metadata.

    This dataclass stores all information about a game, including basic info
    (name, app_id), playtime, categories, metadata (developer, publisher),
    and extended data from external APIs (ProtonDB, Steam Deck, reviews).
    """

    app_id: str
    name: str
    playtime_minutes: int = 0
    last_played: datetime | None = None
    categories: list[str] = None

    # Hidden Status (localconfig)
    hidden: bool = False

    # Metadata
    developer: str = ""
    publisher: str = ""
    release_year: str = ""
    genres: list[str] = None
    tags: list[str] = None
    tag_ids: list[int] = None

    # Sorting
    sort_name: str = ""

    # Override flags
    name_overridden: bool = False

    # Extended data
    proton_db_rating: str = ""
    steam_deck_status: str = ""
    review_score: str = ""
    review_count: int = 0
    review_percentage: int = 0  # Steam review percentage (0-100)
    metacritic_score: int = 0  # Metacritic score (0-100)
    last_updated: str = ""
    steam_grid_db_url: str = ""

    # Legacy / UI Compatibility
    proton_db_tier: str = ""
    steam_review_score: int = 0
    steam_review_desc: str = ""
    steam_review_total: str = ""

    # App type (game, music, tool, application, video, dlc, demo, config)
    app_type: str = ""

    # Platform support (e.g. ["windows", "linux", "mac"])
    platforms: list[str] = None

    # True when loaded from a local Steam manifest (installed on disk)
    installed: bool = False

    # Age Ratings
    pegi_rating: str = ""
    esrb_rating: str = ""

    # HLTB data
    hltb_main_story: float = 0.0
    hltb_main_extras: float = 0.0
    hltb_completionist: float = 0.0

    # Language support (interface languages)
    languages: list[str] = None

    # Achievement data
    achievement_total: int = 0
    achievement_unlocked: int = 0
    achievement_percentage: float = 0.0
    achievement_perfect: bool = False

    # Curator overlap (transient, computed from cache on selection)
    curator_overlap: str = ""

    # Images
    icon_url: str = ""
    cover_url: str = ""

    # Extended metadata (Phase 6.2)
    description: str = ""
    is_private: bool = False
    dlc_ids: list[int] = None
    family_sharing_excluded: bool = False

    def __post_init__(self):
        """Initializes default lists and sort name if missing."""
        if self.categories is None:
            self.categories = []
        if self.genres is None:
            self.genres = []
        if self.tags is None:
            self.tags = []
        if self.tag_ids is None:
            self.tag_ids = []
        if self.platforms is None:
            self.platforms = []
        if self.languages is None:
            self.languages = []
        if self.dlc_ids is None:
            self.dlc_ids = []

        if not self.sort_name:
            self.sort_name = self.name

    @property
    def playtime_hours(self) -> float:
        """Returns playtime in hours, rounded to 1 decimal place.

        Returns:
            Playtime in hours.
        """
        return round(self.playtime_minutes / 60, 1)

    def has_category(self, category: str) -> bool:
        """Checks if the game belongs to a specific category.

        Args:
            category: The category name to check.

        Returns:
            True if the game has this category, False otherwise.
        """
        return category in self.categories

    def is_favorite(self) -> bool:
        """Checks if the game is marked as a favorite.

        Supports localized favorite category names (e.g., 'Favoriten' in German).

        Returns:
            True if the localized 'favorites' category is in the game's categories.
        """
        favorites_key = t("categories.favorites")
        return favorites_key in self.categories


# List of App IDs that are NOT games (Proton, Steam Runtime, etc.)
NON_GAME_APP_IDS: frozenset[str] = frozenset(
    {
        # Proton Versions
        "1493710",  # Proton Experimental
        "2348590",  # Proton Hotfix
        "2230260",  # Proton 7.0
        "2180100",  # Proton 9.0
        "1887720",  # Proton 6.3
        "1826330",  # Proton 8.0
        "1580130",  # Proton 5.13
        "1420170",  # Proton 5.0
        "1245040",  # Proton 4.11
        "1113280",  # Proton 4.2
        "961940",  # Proton 3.16
        "930400",  # Proton 3.7
        "858280",  # Proton 3.7 Beta
        # Steam Linux Runtime
        "1628350",  # Steam Linux Runtime 3.0 (sniper)
        "1391110",  # Steam Linux Runtime 2.0 (soldier)
        "1070560",  # Steam Linux Runtime 1.0 (scout)
        # Steam Tools
        "1517290",  # Steamworks Common Redistributables
        "228980",  # Steamworks Common Redistributables (old)
        "243750",  # Source Filmmaker
        "223530",  # SDK Base 2006
        # Invalid
        "0",  # Invalid/Unknown
    }
)

# List of name patterns for non-games
NON_GAME_NAME_PATTERNS: tuple[str, ...] = (
    "Proton",
    "Steam Linux Runtime",
    "Steamworks Common",
    "Steam Play",
)


NON_GAME_APP_TYPES: frozenset[str] = frozenset({"music", "tool", "application", "video", "dlc", "demo", "config"})

# Ghost entries from appinfo.vdf or cloud storage that have no real name
# Catches: "App 12345", "Unknown App 12345", "Unbekannte App 12345", etc.
_GHOST_NAME_RE: re.Pattern[str] = re.compile(r"^(?:App|Unknown App|Unbekannte App) \d+$")


def is_real_game(game: Game) -> bool:
    """Checks if a game is a real game (not Proton/Steam runtime/tool/soundtrack).

    When ``app_type`` is set, it is used as the primary filter:
    - ``"game"`` or ``""`` (unknown) → falls through to heuristic checks.
    - Any type in ``NON_GAME_APP_TYPES`` → immediately returns False.

    Ghost entries (name matches ``"App <digits>"``) are always excluded,
    regardless of app_type.  These are orphan IDs in cloud storage or
    appinfo.vdf that no longer correspond to a real product.

    Args:
        game: The game to check.

    Returns:
        True if real game, False if tool/runtime/soundtrack/etc.
    """
    # Ghost entries: "App 1002140" etc. — always exclude
    if _GHOST_NAME_RE.match(game.name):
        return False

    # Primary filter: app_type from appinfo.vdf
    if game.app_type:
        if game.app_type.lower() in NON_GAME_APP_TYPES:
            return False
        if game.app_type.lower() == "game":
            return True

    # Heuristic fallback for unknown app_type
    # App ID Check
    if game.app_id in NON_GAME_APP_IDS:
        return False

    # Name Pattern Check
    name_lower = game.name.lower()
    for pattern in NON_GAME_NAME_PATTERNS:
        if pattern.lower() in name_lower:
            return False

    return True
