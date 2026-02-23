"""Batch game query operations.

Handles bulk loading of games and related data using efficient
batch queries instead of N+1 patterns.
"""

from __future__ import annotations

import json
import logging
import sqlite3

from src.core.db.models import DatabaseEntry
from src.utils.i18n import t

logger = logging.getLogger("steamlibmgr.database")

__all__ = ["GameBatchQueryMixin"]


class GameBatchQueryMixin:
    """Mixin providing batch game loading operations.

    Requires ConnectionBase attributes: conn.
    Requires GameQueryMixin: insert_game().
    """

    def batch_insert_games(self, entries: list[DatabaseEntry]) -> int:
        """Insert multiple games in a single transaction.

        Args:
            entries: List of game entries to insert.

        Returns:
            Number of successfully inserted games.
        """
        inserted = 0
        for entry in entries:
            try:
                self.insert_game(entry)
                inserted += 1
            except sqlite3.Error as e:
                logger.warning(t("logs.db.import_failed_app", app_id=entry.app_id, error=str(e)))
        self.conn.commit()
        return inserted

    def get_all_games(self, game_types: set[str] | None = None) -> list[DatabaseEntry]:
        """Get all games from database using efficient batch queries.

        Args:
            game_types: Filter by game types. None = all types.

        Returns:
            List of all games.
        """
        if game_types:
            placeholders = ",".join("?" * len(game_types))
            query = f"SELECT * FROM games WHERE app_type IN ({placeholders})"
            cursor = self.conn.execute(query, tuple(game_types))
        else:
            cursor = self.conn.execute("SELECT * FROM games")

        rows = cursor.fetchall()
        if not rows:
            return []

        app_ids = [row["app_id"] for row in rows]

        # Batch load all related data
        all_genres = self._batch_get_related("game_genres", "genre", app_ids)
        all_tags = self._batch_get_related("game_tags", "tag", app_ids)
        all_franchises = self._batch_get_related("game_franchises", "franchise", app_ids)
        all_languages = self._batch_get_languages(app_ids)
        all_custom_meta = self._batch_get_custom_meta(app_ids)
        all_achievement_stats = self._batch_get_achievement_stats(app_ids)

        games = []
        for row in rows:
            game_data = dict(row)
            aid = game_data["app_id"]

            game_data["genres"] = all_genres.get(aid, [])
            game_data["tags"] = all_tags.get(aid, [])
            game_data["franchises"] = all_franchises.get(aid, [])
            game_data["languages"] = all_languages.get(aid, {})
            game_data["custom_meta"] = all_custom_meta.get(aid, {})
            game_data["platforms"] = json.loads(game_data["platforms"]) if game_data["platforms"] else []

            ach_stats = all_achievement_stats.get(aid)
            if ach_stats:
                total, unlocked, pct, perfect = ach_stats
                game_data["achievements_total"] = total
                game_data["achievement_unlocked"] = unlocked
                game_data["achievement_percentage"] = pct
                game_data["achievement_perfect"] = perfect

            for db_field in ("created_at", "updated_at"):
                game_data.pop(db_field, None)

            games.append(DatabaseEntry(**game_data))

        return games

    def _batch_get_related(self, table: str, column: str, app_ids: list[int]) -> dict[int, list[str]]:
        """Batch load a single-column related table for multiple app_ids.

        Args:
            table: Table name (e.g. 'game_genres').
            column: Value column name (e.g. 'genre').
            app_ids: List of app IDs.

        Returns:
            Dict mapping app_id to list of values.
        """
        if not app_ids:
            return {}

        placeholders = ",".join("?" * len(app_ids))
        cursor = self.conn.execute(f"SELECT app_id, {column} FROM {table} WHERE app_id IN ({placeholders})", app_ids)
        result: dict[int, list[str]] = {}
        for row in cursor.fetchall():
            result.setdefault(row[0], []).append(row[1])
        return result

    def _batch_get_languages(self, app_ids: list[int]) -> dict[int, dict[str, dict[str, bool]]]:
        """Batch load language data for multiple app_ids.

        Args:
            app_ids: List of app IDs.

        Returns:
            Dict mapping app_id to language support data.
        """
        if not app_ids:
            return {}

        placeholders = ",".join("?" * len(app_ids))
        cursor = self.conn.execute(
            f"SELECT app_id, language, interface, audio, subtitles "
            f"FROM game_languages WHERE app_id IN ({placeholders})",
            app_ids,
        )
        result: dict[int, dict[str, dict[str, bool]]] = {}
        for row in cursor.fetchall():
            result.setdefault(row[0], {})[row[1]] = {
                "interface": bool(row[2]),
                "audio": bool(row[3]),
                "subtitles": bool(row[4]),
            }
        return result

    def _batch_get_custom_meta(self, app_ids: list[int]) -> dict[int, dict[str, str]]:
        """Batch load custom metadata for multiple app_ids.

        Args:
            app_ids: List of app IDs.

        Returns:
            Dict mapping app_id to custom metadata.
        """
        if not app_ids:
            return {}

        placeholders = ",".join("?" * len(app_ids))
        cursor = self.conn.execute(
            f"SELECT app_id, key, value FROM game_custom_meta WHERE app_id IN ({placeholders})", app_ids
        )
        result: dict[int, dict[str, str]] = {}
        for row in cursor.fetchall():
            result.setdefault(row[0], {})[row[1]] = row[2]
        return result

    def _batch_get_hltb(self, app_ids: list[int]) -> dict[int, tuple[float, float, float]]:
        """Batch load HLTB hours for multiple app_ids.

        Args:
            app_ids: List of app IDs.

        Returns:
            Dict mapping app_id to (main_story, main_extras, completionist).
        """
        if not app_ids:
            return {}

        placeholders = ",".join("?" * len(app_ids))
        cursor = self.conn.execute(
            f"SELECT app_id, main_story, main_extras, completionist"
            f" FROM hltb_data WHERE app_id IN ({placeholders})"
            f" AND main_story IS NOT NULL",
            app_ids,
        )
        return {row[0]: (float(row[1]), float(row[2] or 0), float(row[3] or 0)) for row in cursor.fetchall()}

    def _batch_get_achievement_stats(self, app_ids: list[int]) -> dict[int, tuple[int, int, float, bool]]:
        """Batch load achievement stats for multiple app_ids.

        Args:
            app_ids: List of app IDs.

        Returns:
            Dict mapping app_id to (total, unlocked, completion_pct, perfect).
        """
        if not app_ids:
            return {}

        placeholders = ",".join("?" * len(app_ids))
        cursor = self.conn.execute(
            f"SELECT app_id, total_achievements, unlocked_achievements, completion_percentage, perfect_game"
            f" FROM achievement_stats WHERE app_id IN ({placeholders})",
            app_ids,
        )
        return {row[0]: (int(row[1]), int(row[2]), float(row[3]), bool(row[4])) for row in cursor.fetchall()}
