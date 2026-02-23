# src/services/filter_constants.py

"""Constants and enums for the view-menu filter system.

Defines all frozenset keys, the SortKey enum, and the type-to-app_type
mapping used by FilterService and other modules.
"""

from __future__ import annotations

from enum import Enum

__all__ = [
    "ALL_ACHIEVEMENT_KEYS",
    "ALL_DECK_KEYS",
    "ALL_LANGUAGE_KEYS",
    "ALL_PEGI_KEYS",
    "ALL_PLATFORM_KEYS",
    "ALL_SORT_KEYS",
    "ALL_STATUS_KEYS",
    "ALL_TYPE_KEYS",
    "SortKey",
    "TYPE_APP_TYPE_MAP",
]


class SortKey(Enum):
    """Available sort keys for the game list.

    Attributes:
        NAME: Sort alphabetically by display name (A-Z).
        PLAYTIME: Sort by total playtime (descending).
        LAST_PLAYED: Sort by last played date (most recent first).
        RELEASE_DATE: Sort by release year (newest first).
    """

    NAME = "name"
    PLAYTIME = "playtime"
    LAST_PLAYED = "last_played"
    RELEASE_DATE = "release_date"


# Maps menu sort key strings to SortKey enum values
ALL_SORT_KEYS: frozenset[str] = frozenset({"name", "playtime", "last_played", "release_date"})

# All known type keys with their matching app_type values
ALL_TYPE_KEYS: frozenset[str] = frozenset({"games", "soundtracks", "software", "videos", "dlcs", "tools"})

# All known platform keys
ALL_PLATFORM_KEYS: frozenset[str] = frozenset({"linux", "windows", "steamos"})

# All known status keys
ALL_STATUS_KEYS: frozenset[str] = frozenset({"installed", "not_installed", "hidden", "with_playtime", "favorites"})

# All known Steam Deck compatibility filter keys
ALL_DECK_KEYS: frozenset[str] = frozenset({"verified", "playable", "unsupported", "unknown"})

# All known achievement filter keys
ALL_ACHIEVEMENT_KEYS: frozenset[str] = frozenset({"perfect", "almost", "progress", "started", "none"})

# All known PEGI age rating filter keys
ALL_PEGI_KEYS: frozenset[str] = frozenset({"pegi_3", "pegi_7", "pegi_12", "pegi_16", "pegi_18", "pegi_none"})

# All known language filter keys
ALL_LANGUAGE_KEYS: frozenset[str] = frozenset(
    {
        "english",
        "german",
        "french",
        "spanish",
        "italian",
        "portuguese",
        "russian",
        "polish",
        "japanese",
        "chinese_simplified",
        "chinese_traditional",
        "korean",
        "dutch",
        "swedish",
        "turkish",
    }
)

# Maps menu type keys to the app_type values they accept
TYPE_APP_TYPE_MAP: dict[str, frozenset[str]] = {
    "games": frozenset({"game", ""}),
    "soundtracks": frozenset({"music"}),
    "software": frozenset({"application"}),
    "videos": frozenset({"video"}),
    "dlcs": frozenset({"dlc"}),
    "tools": frozenset({"tool"}),
}
