"""Database data models and conversion functions.

Contains the core data structures used for database operations:
DatabaseEntry, ImportStats, and conversion utilities.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime, timezone

from src.core.game import Game

__all__ = [
    "DatabaseEntry",
    "ImportStats",
    "database_entry_to_game",
    "is_placeholder_name",
]

_PLACEHOLDER_PATTERN = re.compile(r"^(App \d+|Unknown App \d+|Unbekannte App \d+)$")


def is_placeholder_name(name: str | None) -> bool:
    """Check if a game name is a placeholder/fallback.

    Detects names like "App 123", "Unknown App 123", "Unbekannte App 123"
    which are generated when appinfo.vdf has no real name for an app.

    Args:
        name: The game name to check.

    Returns:
        True if the name is empty, None, or matches a known placeholder pattern.
    """
    if not name or not name.strip():
        return True
    return bool(_PLACEHOLDER_PATTERN.match(name.strip()))


@dataclass(frozen=True)
class ImportStats:
    """Statistics from a database import operation."""

    games_imported: int
    games_updated: int
    games_failed: int
    duration_seconds: float
    source: str


@dataclass
class DatabaseEntry:
    """Single game entry for database operations."""

    app_id: int
    name: str
    app_type: str = "game"
    sort_as: str | None = None
    developer: str | None = None
    publisher: str | None = None

    # Release dates (UNIX timestamps)
    original_release_date: int | None = None
    steam_release_date: int | None = None
    release_date: int | None = None

    # Review data
    review_score: int | None = None  # Steam review category (1-9)
    review_percentage: int | None = None  # Steam review positive percentage (0-100)
    review_count: int | None = None

    # Price & status
    is_free: bool = False
    is_early_access: bool = False

    # Technical features
    vr_support: str = "none"  # none, optional, required
    controller_support: str = "none"  # none, partial, full
    cloud_saves: bool = False
    workshop: bool = False
    trading_cards: bool = False
    achievements_total: int = 0
    achievement_unlocked: int = 0
    achievement_percentage: float = 0.0
    achievement_perfect: bool = False

    # Platform support (JSON array)
    platforms: list[str] = field(default_factory=list)

    # Multi-value fields
    genres: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    franchises: list[str] = field(default_factory=list)
    languages: dict[str, dict[str, bool]] = field(default_factory=dict)

    # Custom metadata
    custom_meta: dict[str, str] = field(default_factory=dict)

    # v8 enrichment cache fields
    pegi_rating: str = ""
    esrb_rating: str = ""
    metacritic_score: int = 0
    steam_deck_status: str = ""
    short_description: str = ""
    content_descriptors: str = ""

    # Metadata management
    is_modified: bool = False
    last_synced: int | None = None
    last_updated: int | None = None


def database_entry_to_game(entry: DatabaseEntry) -> Game:
    """Convert a DatabaseEntry to a Game dataclass.

    Args:
        entry: Database entry to convert.

    Returns:
        Game object populated from the database entry.
    """
    # Extract release year from UNIX timestamp
    release_year = ""
    release_ts = entry.release_date or entry.steam_release_date or entry.original_release_date
    if release_ts and isinstance(release_ts, int) and release_ts > 0:
        release_year = str(datetime.fromtimestamp(release_ts, tz=timezone.utc).year)

    # Extract interface languages from language support data
    interface_languages = [lang for lang, support in entry.languages.items() if support.get("interface", False)]

    return Game(
        app_id=str(entry.app_id),
        name=entry.name,
        sort_name=entry.sort_as or entry.name,
        app_type=entry.app_type or "",
        developer=entry.developer or "",
        publisher=entry.publisher or "",
        release_year=release_year,
        genres=list(entry.genres),
        tags=list(entry.tags),
        platforms=list(entry.platforms),
        languages=interface_languages,
        review_score=str(entry.review_score) if entry.review_score is not None else "",
        review_percentage=entry.review_percentage or 0,
        review_count=entry.review_count or 0,
        last_updated=str(entry.last_updated) if entry.last_updated else "",
        achievement_total=entry.achievements_total,
        achievement_unlocked=entry.achievement_unlocked,
        achievement_percentage=entry.achievement_percentage,
        achievement_perfect=entry.achievement_perfect,
        pegi_rating=entry.pegi_rating or "",
        esrb_rating=entry.esrb_rating or "",
        metacritic_score=entry.metacritic_score or 0,
        steam_deck_status=entry.steam_deck_status or "",
        description=entry.short_description or "",
    )
