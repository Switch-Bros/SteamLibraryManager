# src/utils/tag_resolver.py

"""Steam Tag Resolver: loads tag definitions and resolves TagIDs to names.

Reads the /resources/steamtags/tags_*.txt files (TagID → localized name)
and populates the tag_definitions database table. Provides fast lookups
for TagID → name resolution in the user's language.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.core.database import Database

__all__ = ["TagResolver"]

logger = logging.getLogger("steamlibmgr.tag_resolver")

# Mapping from our steamtags file suffixes to language codes
_LANGUAGE_MAP: dict[str, str] = {
    "en": "en",
    "de": "de",
    "es": "es",
    "fr": "fr",
    "it": "it",
    "ja": "ja",
    "ko": "ko",
    "pt": "pt",
    "zh": "zh",
}

# TagIDs that Steam considers "Genres" (top-level classification).
# These are a subset of regular tags but displayed as genres in the Store.
GENRE_TAG_IDS: frozenset[int] = frozenset(
    {
        9,  # Strategy
        19,  # Action
        21,  # Adventure
        84,  # Design & Illustration
        87,  # Utilities
        113,  # Free to Play
        122,  # RPG
        128,  # Massively Multiplayer
        492,  # Indie
        493,  # Early Access
        597,  # Casual
        599,  # Simulation
        699,  # Racing
        701,  # Sports
    }
)


class TagResolver:
    """Loads and resolves Steam tag definitions.

    Reads TagID → name mappings from resource files and caches them
    in the database for fast lookups.

    Attributes:
        database: The application database.
        steamtags_dir: Path to the steamtags resource directory.
    """

    def __init__(self, database: Database) -> None:
        """Initialize the TagResolver.

        Args:
            database: The application database.
        """
        self.database = database
        self.steamtags_dir = self._find_steamtags_dir()

    @staticmethod
    def _find_steamtags_dir() -> Path:
        """Locate the steamtags resource directory.

        Returns:
            Path to the steamtags directory.
        """
        from src.utils.paths import get_resources_dir

        return get_resources_dir() / "steamtags"

    def ensure_loaded(self) -> int:
        """Ensure tag definitions are loaded into the database.

        Only loads if the tag_definitions table is empty.
        This is safe to call on every startup (fast no-op if already loaded).

        Returns:
            Number of tag definitions in the database.
        """
        count = self.database.get_tag_definitions_count()
        if count > 0:
            return count

        return self.load_all()

    def load_all(self) -> int:
        """Load all tag definition files into the database.

        Reads every tags_*.txt file from the steamtags directory
        and bulk-inserts all (tag_id, language, name) tuples.

        Returns:
            Number of tag definitions loaded.
        """
        if not self.steamtags_dir.exists():
            logger.warning("Steamtags directory not found: %s", self.steamtags_dir)
            return 0

        all_tags: list[tuple[int, str, str]] = []

        for lang_suffix, lang_code in _LANGUAGE_MAP.items():
            file_path = self.steamtags_dir / f"tags_{lang_suffix}.txt"
            if not file_path.exists():
                logger.debug("Tag file not found: %s", file_path)
                continue

            tags = self._parse_tag_file(file_path, lang_code)
            all_tags.extend(tags)

        if not all_tags:
            logger.warning("No tag definitions found in %s", self.steamtags_dir)
            return 0

        count = self.database.populate_tag_definitions(all_tags)
        logger.info("Loaded %d tag definitions (%d languages)", count, len(_LANGUAGE_MAP))
        return count

    @staticmethod
    def _parse_tag_file(file_path: Path, language: str) -> list[tuple[int, str, str]]:
        """Parse a single tags_*.txt file.

        Args:
            file_path: Path to the tag file.
            language: Language code for these tags.

        Returns:
            List of (tag_id, language, name) tuples.
        """
        tags: list[tuple[int, str, str]] = []

        with open(file_path, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line or "\t" not in line:
                    continue

                parts = line.split("\t", maxsplit=1)
                if len(parts) != 2:
                    continue

                try:
                    tag_id = int(parts[0])
                except ValueError:
                    continue

                name = parts[1].strip()
                if name:
                    tags.append((tag_id, language, name))

        return tags

    def resolve_tag_id(self, tag_id: int, language: str = "en") -> str | None:
        """Resolve a single TagID to its localized name.

        Falls back to English if the tag doesn't exist in the requested language.

        Args:
            tag_id: The numeric Steam tag ID.
            language: Target language code.

        Returns:
            The localized tag name, or None if unknown.
        """
        name = self.database.get_tag_name_by_id(tag_id, language)
        if name:
            return name

        # Fallback to English
        if language != "en":
            return self.database.get_tag_name_by_id(tag_id, "en")

        return None

    def resolve_tag_ids(self, tag_ids: list[int], language: str = "en") -> list[str]:
        """Resolve multiple TagIDs to localized names.

        Skips unknown TagIDs silently.

        Args:
            tag_ids: List of numeric Steam tag IDs.
            language: Target language code.

        Returns:
            List of resolved tag names (may be shorter than input).
        """
        names: list[str] = []
        for tid in tag_ids:
            name = self.resolve_tag_id(tid, language)
            if name:
                names.append(name)
        return names

    def get_all_tag_names(self, language: str = "en") -> list[str]:
        """Get all known tag names in a language, sorted alphabetically.

        Args:
            language: Language code.

        Returns:
            Sorted list of tag names.
        """
        return self.database.get_all_tag_names(language)

    def get_genre_names(self, language: str = "en") -> list[str]:
        """Get tag names that Steam considers genres.

        Args:
            language: Language code.

        Returns:
            Sorted list of genre names.
        """
        names: list[str] = []
        for tag_id in sorted(GENRE_TAG_IDS):
            name = self.resolve_tag_id(tag_id, language)
            if name:
                names.append(name)
        return sorted(names)

    def is_genre_tag(self, tag_id: int) -> bool:
        """Check if a TagID is considered a genre.

        Args:
            tag_id: The numeric tag ID.

        Returns:
            True if this tag is a genre-level tag.
        """
        return tag_id in GENRE_TAG_IDS
