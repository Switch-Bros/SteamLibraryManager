"""Single-game CRUD operations.

Handles insert, update, get, delete for individual games,
including related data (genres, tags, franchises, languages, custom_meta).
"""

from __future__ import annotations

import json
import logging
import time

from src.core.db.models import DatabaseEntry, is_placeholder_name

logger = logging.getLogger("steamlibmgr.database")

__all__ = ["GameQueryMixin"]


class GameQueryMixin:
    """Mixin providing single-game CRUD operations.

    Requires ConnectionBase attributes: conn.
    """

    def insert_game(self, entry: DatabaseEntry) -> None:
        """Insert a new game into the database.

        Uses INSERT OR REPLACE which overwrites existing rows.
        Does NOT commit -- caller is responsible for committing.

        Args:
            entry: Game data to insert.
        """
        now = int(time.time())

        self.conn.execute(
            """
            INSERT OR REPLACE INTO games (
                app_id, name, sort_as, app_type,
                developer, publisher,
                original_release_date, steam_release_date, release_date,
                review_score, review_percentage, review_count,
                is_free, is_early_access,
                vr_support, controller_support,
                cloud_saves, workshop, trading_cards, achievements_total,
                platforms,
                pegi_rating, esrb_rating, metacritic_score,
                steam_deck_status, short_description, content_descriptors,
                is_modified, last_synced, last_updated,
                created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                entry.app_id,
                entry.name,
                entry.sort_as,
                entry.app_type,
                entry.developer,
                entry.publisher,
                entry.original_release_date,
                entry.steam_release_date,
                entry.release_date,
                entry.review_score,
                entry.review_percentage,
                entry.review_count,
                entry.is_free,
                entry.is_early_access,
                entry.vr_support,
                entry.controller_support,
                entry.cloud_saves,
                entry.workshop,
                entry.trading_cards,
                entry.achievements_total,
                json.dumps(entry.platforms),
                entry.pegi_rating,
                entry.esrb_rating,
                entry.metacritic_score,
                entry.steam_deck_status,
                entry.short_description,
                entry.content_descriptors,
                entry.is_modified,
                entry.last_synced,
                entry.last_updated,
                now,
                now,
            ),
        )

        self._insert_related_data(entry)

    def update_game(self, entry: DatabaseEntry) -> None:
        """Update an existing game, preserving created_at.

        Protects good names: if the existing game has a real name and the
        incoming entry has a placeholder or empty name, the existing name
        is preserved.

        Args:
            entry: Updated game data.
        """
        now = int(time.time())

        existing = self.conn.execute("SELECT created_at, name FROM games WHERE app_id = ?", (entry.app_id,)).fetchone()

        if existing:
            # Protect good names from being overwritten by placeholders
            existing_name = existing["name"] if existing["name"] else ""
            if not is_placeholder_name(existing_name) and is_placeholder_name(entry.name):
                entry_name = existing_name
            else:
                entry_name = entry.name

            self.conn.execute(
                """
                UPDATE games SET
                    name = ?, sort_as = ?, app_type = ?,
                    developer = ?, publisher = ?,
                    original_release_date = ?, steam_release_date = ?, release_date = ?,
                    review_score = ?, review_percentage = ?, review_count = ?,
                    is_free = ?, is_early_access = ?,
                    vr_support = ?, controller_support = ?,
                    cloud_saves = ?, workshop = ?, trading_cards = ?, achievements_total = ?,
                    platforms = ?,
                    pegi_rating = ?, esrb_rating = ?, metacritic_score = ?,
                    steam_deck_status = ?, short_description = ?, content_descriptors = ?,
                    is_modified = ?, last_synced = ?, last_updated = ?,
                    updated_at = ?
                WHERE app_id = ?
                """,
                (
                    entry_name,
                    entry.sort_as,
                    entry.app_type,
                    entry.developer,
                    entry.publisher,
                    entry.original_release_date,
                    entry.steam_release_date,
                    entry.release_date,
                    entry.review_score,
                    entry.review_percentage,
                    entry.review_count,
                    entry.is_free,
                    entry.is_early_access,
                    entry.vr_support,
                    entry.controller_support,
                    entry.cloud_saves,
                    entry.workshop,
                    entry.trading_cards,
                    entry.achievements_total,
                    json.dumps(entry.platforms),
                    entry.pegi_rating,
                    entry.esrb_rating,
                    entry.metacritic_score,
                    entry.steam_deck_status,
                    entry.short_description,
                    entry.content_descriptors,
                    entry.is_modified,
                    entry.last_synced,
                    entry.last_updated,
                    now,
                    entry.app_id,
                ),
            )

            # Re-insert related data (delete old first)
            for table in ("game_genres", "game_tags", "game_franchises", "game_languages", "game_custom_meta"):
                self.conn.execute(f"DELETE FROM {table} WHERE app_id = ?", (entry.app_id,))

            self._insert_related_data(entry)
        else:
            self.insert_game(entry)

    def _insert_related_data(self, entry: DatabaseEntry) -> None:
        """Insert genre/tag/franchise/language/custom_meta rows for a game.

        Args:
            entry: Game entry whose related data to insert.
        """
        if entry.genres:
            self.conn.executemany(
                "INSERT OR REPLACE INTO game_genres (app_id, genre) VALUES (?, ?)",
                [(entry.app_id, genre) for genre in entry.genres],
            )
        if entry.tags:
            self.conn.executemany(
                "INSERT OR REPLACE INTO game_tags (app_id, tag) VALUES (?, ?)",
                [(entry.app_id, tag) for tag in entry.tags],
            )
        if entry.franchises:
            self.conn.executemany(
                "INSERT OR REPLACE INTO game_franchises (app_id, franchise) VALUES (?, ?)",
                [(entry.app_id, franchise) for franchise in entry.franchises],
            )
        if entry.languages:
            language_rows = []
            for lang, support in entry.languages.items():
                language_rows.append(
                    (
                        entry.app_id,
                        lang,
                        support.get("interface", False),
                        support.get("audio", False),
                        support.get("subtitles", False),
                    )
                )
            self.conn.executemany(
                """
                INSERT OR REPLACE INTO game_languages
                (app_id, language, interface, audio, subtitles)
                VALUES (?, ?, ?, ?, ?)
                """,
                language_rows,
            )
        if entry.custom_meta:
            self.conn.executemany(
                "INSERT OR REPLACE INTO game_custom_meta (app_id, key, value) VALUES (?, ?, ?)",
                [(entry.app_id, key, value) for key, value in entry.custom_meta.items()],
            )

    def get_game(self, app_id: int) -> DatabaseEntry | None:
        """Get a single game by app ID.

        Args:
            app_id: Steam app ID.

        Returns:
            Game data or None if not found.
        """
        cursor = self.conn.execute("SELECT * FROM games WHERE app_id = ?", (app_id,))
        row = cursor.fetchone()

        if not row:
            return None

        game_data = dict(row)

        # Load related data
        game_data["genres"] = self._get_genres(app_id)
        game_data["tags"] = self._get_tags(app_id)
        game_data["franchises"] = self._get_franchises(app_id)
        game_data["languages"] = self._get_languages(app_id)
        game_data["custom_meta"] = self._get_custom_meta(app_id)

        # Parse JSON fields
        game_data["platforms"] = json.loads(game_data["platforms"]) if game_data["platforms"] else []

        # Load achievement stats for this game
        ach_cursor = self.conn.execute(
            "SELECT total_achievements, unlocked_achievements, completion_percentage, perfect_game"
            " FROM achievement_stats WHERE app_id = ?",
            (app_id,),
        )
        ach_row = ach_cursor.fetchone()
        if ach_row:
            game_data["achievements_total"] = int(ach_row[0])
            game_data["achievement_unlocked"] = int(ach_row[1])
            game_data["achievement_percentage"] = float(ach_row[2])
            game_data["achievement_perfect"] = bool(ach_row[3])

        # Remove DB-only fields not in DatabaseEntry
        for db_field in ("created_at", "updated_at"):
            game_data.pop(db_field, None)

        return DatabaseEntry(**game_data)

    def get_app_type_lookup(self) -> dict[str, tuple[str, str]]:
        """Returns a fast lookup of app_id to (app_type, name) for all games.

        Returns:
            Dict mapping app_id (str) to (app_type, name) tuples.
        """
        cursor = self.conn.execute("SELECT app_id, app_type, name FROM games")
        return {str(row[0]): (row[1], row[2]) for row in cursor.fetchall()}

    def get_game_count(self) -> int:
        """Get total number of games in the database.

        Returns:
            Number of games.
        """
        cursor = self.conn.execute("SELECT COUNT(*) FROM games")
        return cursor.fetchone()[0]

    def update_game_name(self, app_id: int, name: str) -> None:
        """Updates the name of a game in the database.

        Args:
            app_id: Steam app ID.
            name: New name for the game.
        """
        self.conn.execute("UPDATE games SET name = ? WHERE app_id = ?", (name, app_id))

    def delete_game(self, app_id: int) -> None:
        """Delete a game from database.

        Args:
            app_id: Steam app ID.
        """
        self.conn.execute("DELETE FROM games WHERE app_id = ?", (app_id,))

    # -- Single-game helpers (used by get_game) --

    def _get_genres(self, app_id: int) -> list[str]:
        """Get genres for a game."""
        cursor = self.conn.execute("SELECT genre FROM game_genres WHERE app_id = ?", (app_id,))
        return [row[0] for row in cursor.fetchall()]

    def _get_tags(self, app_id: int) -> list[str]:
        """Get tags for a game."""
        cursor = self.conn.execute("SELECT tag FROM game_tags WHERE app_id = ?", (app_id,))
        return [row[0] for row in cursor.fetchall()]

    def _get_franchises(self, app_id: int) -> list[str]:
        """Get franchises for a game."""
        cursor = self.conn.execute("SELECT franchise FROM game_franchises WHERE app_id = ?", (app_id,))
        return [row[0] for row in cursor.fetchall()]

    def _get_languages(self, app_id: int) -> dict[str, dict[str, bool]]:
        """Get language support for a game."""
        cursor = self.conn.execute(
            "SELECT language, interface, audio, subtitles FROM game_languages WHERE app_id = ?", (app_id,)
        )
        languages: dict[str, dict[str, bool]] = {}
        for row in cursor.fetchall():
            languages[row[0]] = {"interface": bool(row[1]), "audio": bool(row[2]), "subtitles": bool(row[3])}
        return languages

    def _get_custom_meta(self, app_id: int) -> dict[str, str]:
        """Get custom metadata for a game."""
        cursor = self.conn.execute("SELECT key, value FROM game_custom_meta WHERE app_id = ?", (app_id,))
        return {row[0]: row[1] for row in cursor.fetchall()}
