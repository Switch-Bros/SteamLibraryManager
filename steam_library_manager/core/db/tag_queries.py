"""Tag definition and game-tag association queries.

Handles tag definitions (TagID -> name), game-tag associations,
and bulk review percentage updates.
"""

from __future__ import annotations

import logging

logger = logging.getLogger("steamlibmgr.database")

__all__ = ["TagQueryMixin"]


class TagQueryMixin:
    """Mixin providing tag definition and related queries.

    Requires ConnectionBase attributes: conn.
    """

    def populate_tag_definitions(self, tags: list[tuple[int, str, str]]) -> int:
        """Bulk-insert tag definitions (TagID -> localized name).

        Args:
            tags: List of (tag_id, language, name) tuples.

        Returns:
            Number of tags inserted.
        """
        self.conn.executemany(
            "INSERT OR REPLACE INTO tag_definitions (tag_id, language, name) VALUES (?, ?, ?)",
            tags,
        )
        self.conn.commit()
        return len(tags)

    def get_tag_definitions_count(self) -> int:
        """Get number of tag definitions in the database.

        Returns:
            Total count of tag definition rows.
        """
        cursor = self.conn.execute("SELECT COUNT(*) FROM tag_definitions")
        return cursor.fetchone()[0]

    def get_all_tag_names(self, language: str = "en") -> list[str]:
        """Get all known tag names for a language, sorted alphabetically.

        Args:
            language: Language code (e.g. 'en', 'de').

        Returns:
            Sorted list of tag names.
        """
        cursor = self.conn.execute(
            "SELECT name FROM tag_definitions WHERE language = ? ORDER BY name",
            (language,),
        )
        return [row[0] for row in cursor.fetchall()]

    def get_tag_id_by_name(self, name: str, language: str = "en") -> int | None:
        """Look up a TagID by its localized name.

        Args:
            name: The tag name to look up.
            language: Language code.

        Returns:
            TagID or None if not found.
        """
        cursor = self.conn.execute(
            "SELECT tag_id FROM tag_definitions WHERE name = ? AND language = ? LIMIT 1",
            (name, language),
        )
        row = cursor.fetchone()
        return row[0] if row else None

    def get_tag_name_by_id(self, tag_id: int, language: str = "en") -> str | None:
        """Resolve a TagID to its localized name.

        Args:
            tag_id: The numeric tag ID.
            language: Language code.

        Returns:
            Tag name or None if not found.
        """
        cursor = self.conn.execute(
            "SELECT name FROM tag_definitions WHERE tag_id = ? AND language = ? LIMIT 1",
            (tag_id, language),
        )
        row = cursor.fetchone()
        return row[0] if row else None

    def bulk_insert_game_tags_by_id(self, game_tags: list[tuple[int, int, str]]) -> int:
        """Bulk-insert game-tag associations using TagIDs.

        Args:
            game_tags: List of (app_id, tag_id, tag_name) tuples.

        Returns:
            Number of rows inserted.
        """
        self.conn.executemany(
            "INSERT OR REPLACE INTO game_tags (app_id, tag, tag_id) VALUES (?, ?, ?)",
            [(app_id, name, tag_id) for app_id, tag_id, name in game_tags],
        )
        return len(game_tags)

    def get_game_tag_count(self) -> int:
        """Get total number of game-tag associations.

        Returns:
            Count of rows in game_tags.
        """
        cursor = self.conn.execute("SELECT COUNT(*) FROM game_tags")
        return cursor.fetchone()[0]

    def get_all_app_ids(self) -> set[int]:
        """Get all app_ids that exist in the games table.

        Returns:
            Set of all app_ids in the games table.
        """
        cursor = self.conn.execute("SELECT app_id FROM games")
        return {row[0] for row in cursor.fetchall()}

    def bulk_update_review_percentages(self, percentages: list[tuple[int, int]]) -> int:
        """Batch-update review_percentage in the games table.

        Args:
            percentages: List of (review_percentage, app_id) tuples.

        Returns:
            Number of rows updated.
        """
        self.conn.executemany(
            "UPDATE games SET review_percentage = ? WHERE app_id = ?",
            percentages,
        )
        return len(percentages)
