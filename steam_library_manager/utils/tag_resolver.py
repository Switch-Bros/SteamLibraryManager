#
# steam_library_manager/utils/tag_resolver.py
# Steam tag resolver - loads tag definitions and resolves TagIDs to names
#
# Copyright © 2025-2026 SwitchBros
# Licensed under the MIT License. See LICENSE for details.
#
from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from steam_library_manager.core.database import Database

__all__ = ["TagResolver"]

logger = logging.getLogger("steamlibmgr.tag_resolver")

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
    """Loads and resolves Steam tag definitions."""

    def __init__(self, database: Database) -> None:
        self.database = database
        self.steamtags_dir = self._find_steamtags_dir()

    @staticmethod
    def _find_steamtags_dir() -> Path:
        from steam_library_manager.utils.paths import get_resources_dir

        return get_resources_dir() / "steamtags"

    def ensure_loaded(self) -> int:
        """Ensure tag definitions are loaded; no-op if already present."""
        count = self.database.get_tag_definitions_count()
        if count > 0:
            return count

        return self.load_all()

    def load_all(self) -> int:
        """Load all tag definition files into the database."""
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
        """Parse a single tags_*.txt file into (tag_id, language, name) tuples."""
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
        """Resolve a single TagID to its localized name, falling back to English."""
        name = self.database.get_tag_name_by_id(tag_id, language)
        if name:
            return name

        if language != "en":
            return self.database.get_tag_name_by_id(tag_id, "en")

        return None

    def resolve_tag_ids(self, tag_ids: list[int], language: str = "en") -> list[str]:
        """Resolve multiple TagIDs to localized names, skipping unknown ones."""
        names: list[str] = []
        for tid in tag_ids:
            name = self.resolve_tag_id(tid, language)
            if name:
                names.append(name)
        return names

    def get_all_tag_names(self, language: str = "en") -> list[str]:
        """Get all known tag names in a language, sorted alphabetically."""
        return self.database.get_all_tag_names(language)

    def get_genre_names(self, language: str = "en") -> list[str]:
        """Get tag names that Steam considers genres."""
        names: list[str] = []
        for tag_id in sorted(GENRE_TAG_IDS):
            name = self.resolve_tag_id(tag_id, language)
            if name:
                names.append(name)
        return sorted(names)

    def is_genre_tag(self, tag_id: int) -> bool:
        """Check if a TagID is considered a genre."""
        return tag_id in GENRE_TAG_IDS
