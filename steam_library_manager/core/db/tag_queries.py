#
# steam_library_manager/core/db/tag_queries.py
# Tag definitions, game-tag associations, and bulk review updates
#
# Copyright © 2025-2026 SwitchBros
# Licensed under the MIT License. See LICENSE for details.
#

from __future__ import annotations

import logging

logger = logging.getLogger("steamlibmgr.database")

__all__ = ["TagQueryMixin"]


class TagQueryMixin:
    """Tag definitions and game-tag queries. Requires ``conn``."""

    def populate_tag_definitions(self, tags: list[tuple[int, str, str]]) -> int:
        """Bulk upsert tag definitions. Returns count."""
        self.conn.executemany(
            "INSERT OR REPLACE INTO tag_definitions (tag_id, language, name) VALUES (?, ?, ?)",
            tags,
        )
        self.conn.commit()
        return len(tags)

    def get_tag_definitions_count(self) -> int:
        cursor = self.conn.execute("SELECT COUNT(*) FROM tag_definitions")
        return cursor.fetchone()[0]

    def get_all_tag_names(self, language: str = "en") -> list[str]:
        """All tag names for a language, sorted alphabetically."""
        cursor = self.conn.execute(
            "SELECT name FROM tag_definitions WHERE language = ? ORDER BY name",
            (language,),
        )
        return [row[0] for row in cursor.fetchall()]

    def get_tag_id_by_name(self, name: str, language: str = "en") -> int | None:
        cursor = self.conn.execute(
            "SELECT tag_id FROM tag_definitions WHERE name = ? AND language = ? LIMIT 1",
            (name, language),
        )
        row = cursor.fetchone()
        return row[0] if row else None

    def get_tag_name_by_id(self, tag_id: int, language: str = "en") -> str | None:
        cursor = self.conn.execute(
            "SELECT name FROM tag_definitions WHERE tag_id = ? AND language = ? LIMIT 1",
            (tag_id, language),
        )
        row = cursor.fetchone()
        return row[0] if row else None

    def bulk_insert_game_tags_by_id(self, game_tags: list[tuple[int, int, str]]) -> int:
        """Bulk upsert game-tag associations. Returns row count."""
        self.conn.executemany(
            "INSERT OR REPLACE INTO game_tags (app_id, tag, tag_id) VALUES (?, ?, ?)",
            [(app_id, name, tag_id) for app_id, tag_id, name in game_tags],
        )
        return len(game_tags)

    def get_game_tag_count(self) -> int:
        cursor = self.conn.execute("SELECT COUNT(*) FROM game_tags")
        return cursor.fetchone()[0]

    def get_all_app_ids(self) -> set[int]:
        """All app_ids in the games table."""
        cursor = self.conn.execute("SELECT app_id FROM games")
        return {row[0] for row in cursor.fetchall()}

    def bulk_update_review_percentages(self, percentages: list[tuple[int, int]]) -> int:
        """Batch-update review_percentage. Returns update count."""
        self.conn.executemany(
            "UPDATE games SET review_percentage = ? WHERE app_id = ?",
            percentages,
        )
        return len(percentages)
