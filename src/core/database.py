"""Steam Library Manager - Database Module.

SQLite-based metadata cache to avoid parsing appinfo.vdf on every startup.
Performance: < 3 seconds startup vs 30+ seconds with direct VDF parsing.

Architecture:
    Valve Files (READ ONCE) -> SQLite (PRIMARY STORAGE) -> App Memory
                    |
            Only write when user changes metadata!
"""

from __future__ import annotations

import json
import logging
import re
import sqlite3
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.core.game import Game
from src.utils.i18n import t

logger = logging.getLogger("steamlibmgr.database")

__all__ = [
    "Database",
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
    review_score: int | None = None  # 0-100
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
        review_count=entry.review_count or 0,
        last_updated=str(entry.last_updated) if entry.last_updated else "",
        achievement_total=entry.achievements_total,
        achievement_unlocked=entry.achievement_unlocked,
        achievement_percentage=entry.achievement_percentage,
        achievement_perfect=entry.achievement_perfect,
    )


class Database:
    """SQLite database manager for Steam game metadata.

    Handles schema creation/migrations, CRUD operations, batch imports,
    modification tracking, and fast queries for UI.
    """

    SCHEMA_VERSION = 5

    def __init__(self, db_path: Path):
        """Initialize database connection.

        Args:
            db_path: Path to SQLite database file.
        """
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        self.conn = sqlite3.connect(str(db_path))
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON")
        self.conn.execute("PRAGMA journal_mode = WAL")

        self._ensure_schema()

    def _ensure_schema(self) -> None:
        """Create or migrate database schema."""
        current_version = self._get_schema_version()

        if current_version == 0:
            self._create_schema()
            self._set_schema_version(self.SCHEMA_VERSION)
        elif current_version < self.SCHEMA_VERSION:
            self._migrate(current_version, self.SCHEMA_VERSION)

    def _get_schema_version(self) -> int:
        """Get current database schema version."""
        try:
            cursor = self.conn.execute("SELECT MAX(version) FROM schema_version")
            result = cursor.fetchone()
            return result[0] if result[0] is not None else 0
        except sqlite3.OperationalError:
            return 0

    def _set_schema_version(self, version: int) -> None:
        """Set database schema version."""
        self.conn.execute(
            """
            INSERT OR REPLACE INTO schema_version (version, applied_at, description)
            VALUES (?, ?, ?)
            """,
            (version, int(time.time()), t("logs.db.schema_created")),
        )
        self.conn.commit()

    def _create_schema(self) -> None:
        """Create initial database schema from SQL file."""
        schema_path = Path(__file__).parent / "database_schema.sql"
        try:
            with open(schema_path) as f:
                schema_sql = f.read()
        except FileNotFoundError:
            logger.error(t("logs.db.schema_not_found", path=str(schema_path)))
            raise

        try:
            self.conn.executescript(schema_sql)
            self.conn.commit()
            logger.info(t("logs.db.schema_created"))
        except sqlite3.Error as e:
            logger.error(t("logs.db.schema_error", error=str(e)))
            raise

    def _migrate(self, from_version: int, to_version: int) -> None:
        """Migrate database schema.

        Args:
            from_version: Current schema version.
            to_version: Target schema version.
        """
        logger.info(
            "Migrating database from version %d to %d",
            from_version,
            to_version,
        )

        if from_version < 3:
            self._migrate_to_v3()
            self._set_schema_version(3)

        if from_version < 4:
            self._migrate_to_v4()
            self._set_schema_version(4)

        if from_version < 5:
            self._migrate_to_v5()
            self._set_schema_version(5)

    def _migrate_to_v3(self) -> None:
        """Migrate to schema v3: tag_definitions table + tag_id column."""
        # Add tag_id column to game_tags (if not exists)
        try:
            self.conn.execute("ALTER TABLE game_tags ADD COLUMN tag_id INTEGER")
        except sqlite3.OperationalError:
            pass  # Column already exists

        # Create tag_definitions table
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS tag_definitions (
                tag_id INTEGER NOT NULL,
                language TEXT NOT NULL,
                name TEXT NOT NULL,
                PRIMARY KEY (tag_id, language)
            )
            """)
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_tags_tag_id ON game_tags(tag_id)")
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_tag_definitions_name ON tag_definitions(name)")
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_tag_definitions_lang ON tag_definitions(language)")
        self.conn.commit()
        logger.info("Migrated to schema v3: tag_definitions + tag_id")

    def _migrate_to_v4(self) -> None:
        """Migrate to schema v4: hltb_id_cache table."""
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS hltb_id_cache (
                steam_app_id INTEGER PRIMARY KEY,
                hltb_game_id INTEGER NOT NULL,
                cached_at INTEGER NOT NULL
            )
            """)
        self.conn.commit()
        logger.info("Migrated to schema v4: hltb_id_cache")

    def _migrate_to_v5(self) -> None:
        """Migrate to schema v5: protondb_ratings table."""
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS protondb_ratings (
                app_id INTEGER PRIMARY KEY,
                tier TEXT NOT NULL,
                confidence TEXT DEFAULT '',
                trending_tier TEXT DEFAULT '',
                score REAL DEFAULT 0.0,
                best_reported TEXT DEFAULT '',
                last_updated INTEGER NOT NULL
            )
            """)
        self.conn.commit()
        logger.info("Migrated to schema v5: protondb_ratings")

    # ========================================================================
    # GAME CRUD OPERATIONS
    # ========================================================================

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
                review_score, review_count,
                is_free, is_early_access,
                vr_support, controller_support,
                cloud_saves, workshop, trading_cards, achievements_total,
                platforms,
                is_modified, last_synced, last_updated,
                created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                entry.is_modified,
                entry.last_synced,
                entry.last_updated,
                now,
                now,
            ),
        )

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

    def update_game(self, entry: DatabaseEntry) -> None:
        """Update an existing game, preserving created_at.

        Protects good names: if the existing game has a real name and the
        incoming entry has a placeholder or empty name, the existing name
        is preserved.

        Args:
            entry: Updated game data.
        """
        now = int(time.time())

        # Check if game exists to preserve created_at and name
        existing = self.conn.execute("SELECT created_at, name FROM games WHERE app_id = ?", (entry.app_id,)).fetchone()

        if existing:
            # Protect good names from being overwritten by placeholders
            existing_name = existing["name"] if existing["name"] else ""
            if not is_placeholder_name(existing_name) and is_placeholder_name(entry.name):
                entry_name = existing_name
            else:
                entry_name = entry.name

            # True UPDATE preserving created_at
            self.conn.execute(
                """
                UPDATE games SET
                    name = ?, sort_as = ?, app_type = ?,
                    developer = ?, publisher = ?,
                    original_release_date = ?, steam_release_date = ?, release_date = ?,
                    review_score = ?, review_count = ?,
                    is_free = ?, is_early_access = ?,
                    vr_support = ?, controller_support = ?,
                    cloud_saves = ?, workshop = ?, trading_cards = ?, achievements_total = ?,
                    platforms = ?,
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

            # Re-insert related data via shared logic
            self._insert_related_data(entry)
        else:
            # Game does not exist, do a full insert
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

    def get_all_games(self, game_types: set[str] | None = None) -> list[DatabaseEntry]:
        """Get all games from database using efficient batch queries.

        Replaces the N+1 query pattern with a single pass over games + batch
        loading of related data.

        Args:
            game_types: Filter by game types. None = all types.

        Returns:
            List of all games.
        """
        # Load all game rows in one query
        if game_types:
            placeholders = ",".join("?" * len(game_types))
            query = f"SELECT * FROM games WHERE app_type IN ({placeholders})"
            cursor = self.conn.execute(query, tuple(game_types))
        else:
            cursor = self.conn.execute("SELECT * FROM games")

        rows = cursor.fetchall()
        if not rows:
            return []

        # Collect all app_ids for batch loading related data
        app_ids = [row["app_id"] for row in rows]

        # Batch load all related data
        all_genres = self._batch_get_related("game_genres", "genre", app_ids)
        all_tags = self._batch_get_related("game_tags", "tag", app_ids)
        all_franchises = self._batch_get_related("game_franchises", "franchise", app_ids)
        all_languages = self._batch_get_languages(app_ids)
        all_custom_meta = self._batch_get_custom_meta(app_ids)

        # Batch load achievement stats
        all_achievement_stats = self._batch_get_achievement_stats(app_ids)

        # Build DatabaseEntry objects
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

            # Populate achievement stats from batch query
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

    def get_app_type_lookup(self) -> dict[str, tuple[str, str]]:
        """Returns a fast lookup of app_id to (app_type, name) for all games.

        Used during startup to replace thousands of individual
        appinfo_manager.get_app_metadata() calls with a single DB query.

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

    def delete_game(self, app_id: int) -> None:
        """Delete a game from database.

        Args:
            app_id: Steam app ID.
        """
        self.conn.execute("DELETE FROM games WHERE app_id = ?", (app_id,))

    # ========================================================================
    # BATCH HELPER METHODS FOR RELATED DATA
    # ========================================================================

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

    # Single-game helpers (used by get_game)
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

    # ========================================================================
    # MODIFICATION TRACKING
    # ========================================================================

    def track_modification(self, app_id: int, original_data: dict[str, Any], modified_data: dict[str, Any]) -> None:
        """Track a metadata modification.

        Args:
            app_id: Steam app ID.
            original_data: Original metadata before modification.
            modified_data: Modified metadata.
        """
        self.conn.execute(
            """
            INSERT OR REPLACE INTO metadata_modifications
            (app_id, original_data, modified_data, modification_time, synced_to_appinfo)
            VALUES (?, ?, ?, ?, 0)
            """,
            (app_id, json.dumps(original_data), json.dumps(modified_data), int(time.time())),
        )
        self.conn.commit()

    def get_modified_games(self, synced_only: bool = False) -> dict[int, dict[str, Any]]:
        """Get all modified games.

        Args:
            synced_only: If True, only return games not yet synced to appinfo.vdf.

        Returns:
            Dict mapping app_id to modification data.
        """
        query = "SELECT * FROM metadata_modifications"
        if synced_only:
            query += " WHERE synced_to_appinfo = 0"

        cursor = self.conn.execute(query)

        modifications: dict[int, dict[str, Any]] = {}
        for row in cursor.fetchall():
            modifications[row["app_id"]] = {
                "original": json.loads(row["original_data"]),
                "modified": json.loads(row["modified_data"]),
                "modification_time": row["modification_time"],
                "synced": bool(row["synced_to_appinfo"]),
                "sync_time": row["sync_time"],
            }

        return modifications

    def mark_synced(self, app_id: int) -> None:
        """Mark a game as synced to appinfo.vdf.

        Args:
            app_id: Steam app ID.
        """
        self.conn.execute(
            """
            UPDATE metadata_modifications
            SET synced_to_appinfo = 1, sync_time = ?
            WHERE app_id = ?
            """,
            (int(time.time()), app_id),
        )
        self.conn.execute("UPDATE games SET last_synced = ? WHERE app_id = ?", (int(time.time()), app_id))
        self.conn.commit()

    def revert_modification(self, app_id: int) -> DatabaseEntry | None:
        """Revert a game to its original state.

        Args:
            app_id: Steam app ID.

        Returns:
            Original game data or None if not found.
        """
        cursor = self.conn.execute("SELECT original_data FROM metadata_modifications WHERE app_id = ?", (app_id,))
        row = cursor.fetchone()

        if not row:
            return None

        original_data = json.loads(row[0])

        entry = DatabaseEntry(app_id=app_id, **original_data)
        self.update_game(entry)

        self.conn.execute("DELETE FROM metadata_modifications WHERE app_id = ?", (app_id,))
        self.conn.commit()

        return entry

    # ========================================================================
    # IMPORT OPERATIONS
    # ========================================================================

    def record_import(self, stats: ImportStats) -> None:
        """Record import statistics.

        Args:
            stats: Import statistics.
        """
        self.conn.execute(
            """
            INSERT INTO import_history
            (import_time, source, games_imported, games_updated, games_failed, notes)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                int(time.time()),
                stats.source,
                stats.games_imported,
                stats.games_updated,
                stats.games_failed,
                t("logs.db.import_duration", duration=f"{stats.duration_seconds:.2f}"),
            ),
        )
        self.conn.commit()

    # ========================================================================
    # DATA QUALITY
    # ========================================================================

    def repair_placeholder_names(self) -> int:
        """Replace placeholder names with empty strings in the database.

        Finds entries with names like "App 123", "Unknown App 123", or
        "Unbekannte App 123" and clears them so that enrichment can
        fill in real names from other sources.

        Returns:
            Number of names cleaned.
        """
        cursor = self.conn.execute("""
            SELECT COUNT(*) FROM games
            WHERE name GLOB 'App [0-9]*'
               OR name GLOB 'Unknown App [0-9]*'
               OR name GLOB 'Unbekannte App [0-9]*'
            """)
        count = cursor.fetchone()[0]

        if count > 0:
            self.conn.execute(
                """
                UPDATE games SET name = '', updated_at = ?
                WHERE name GLOB 'App [0-9]*'
                   OR name GLOB 'Unknown App [0-9]*'
                   OR name GLOB 'Unbekannte App [0-9]*'
                """,
                (int(time.time()),),
            )
            self.conn.commit()
            logger.info(t("logs.db.repaired_placeholders", count=count))

        return count

    # ========================================================================
    # ENRICHMENT QUERIES (Phase 5)
    # ========================================================================

    def upsert_game_metadata(self, app_id: int, **fields: Any) -> None:
        """Updates specific metadata fields for an existing game.

        Only updates the provided fields; other columns remain unchanged.
        Silently does nothing if the game does not exist.

        Args:
            app_id: Steam app ID.
            **fields: Column name/value pairs to update (e.g. developer="Valve").
        """
        if not fields:
            return

        # Filter to valid column names to prevent SQL injection
        valid_columns = {
            "name",
            "sort_as",
            "app_type",
            "developer",
            "publisher",
            "original_release_date",
            "steam_release_date",
            "release_date",
            "review_score",
            "review_count",
            "is_free",
            "is_early_access",
            "vr_support",
            "controller_support",
            "cloud_saves",
            "workshop",
            "trading_cards",
            "achievements_total",
            "platforms",
        }
        safe_fields = {k: v for k, v in fields.items() if k in valid_columns}
        if not safe_fields:
            return

        set_clause = ", ".join(f"{col} = ?" for col in safe_fields)
        values = list(safe_fields.values()) + [int(time.time()), app_id]

        self.conn.execute(
            f"UPDATE games SET {set_clause}, updated_at = ? WHERE app_id = ?",
            values,
        )

    def upsert_languages(self, app_id: int, languages: dict[str, dict[str, bool]]) -> None:
        """Replaces language support data for a game.

        Deletes existing language rows and inserts the new ones.

        Args:
            app_id: Steam app ID.
            languages: Dict mapping language name to support flags
                (interface, audio, subtitles).
        """
        if not languages:
            return

        self.conn.execute("DELETE FROM game_languages WHERE app_id = ?", (app_id,))

        rows = [
            (
                app_id,
                lang,
                support.get("interface", False),
                support.get("audio", False),
                support.get("subtitles", False),
            )
            for lang, support in languages.items()
        ]
        self.conn.executemany(
            "INSERT OR REPLACE INTO game_languages"
            " (app_id, language, interface, audio, subtitles)"
            " VALUES (?, ?, ?, ?, ?)",
            rows,
        )

    def get_all_game_ids(self) -> list[tuple[int, str]]:
        """Returns all game-type apps from the database.

        Used by force-refresh enrichment to re-process all games
        regardless of existing data.

        Returns:
            List of (app_id, name) tuples for all games.
        """
        cursor = self.conn.execute("SELECT app_id, name FROM games WHERE app_type IN ('game', '')")
        return [(row[0], row[1]) for row in cursor.fetchall()]

    def get_apps_missing_metadata(self) -> list[tuple[int, str]]:
        """Returns apps with missing developer, publisher, or release date.

        Returns:
            List of (app_id, name) tuples for games where any of
            developer, publisher, or release date is missing.
        """
        cursor = self.conn.execute(
            "SELECT app_id, name FROM games"
            " WHERE (developer IS NULL OR developer = '')"
            " OR (publisher IS NULL OR publisher = '')"
            " OR ("
            "   (original_release_date IS NULL OR original_release_date = 0)"
            "   AND (steam_release_date IS NULL OR steam_release_date = 0)"
            " )"
        )
        return [(row[0], row[1]) for row in cursor.fetchall()]

    def get_apps_without_hltb(self) -> list[tuple[int, str]]:
        """Returns game-type apps that have no HLTB data.

        Returns:
            List of (app_id, name) tuples for games without HLTB records.
        """
        cursor = self.conn.execute("""
            SELECT g.app_id, g.name FROM games g
            LEFT JOIN hltb_data h ON g.app_id = h.app_id
            WHERE h.app_id IS NULL AND g.app_type IN ('game', '')
            """)
        return [(row[0], row[1]) for row in cursor.fetchall()]

    # ========================================================================
    # HLTB ID CACHE (Phase 5.5)
    # ========================================================================

    _HLTB_CACHE_TTL_DAYS = 30

    def load_hltb_id_cache(self) -> dict[int, int]:
        """Loads the steam_app_id → hltb_game_id cache from database.

        Only returns entries younger than 30 days.

        Returns:
            Dict mapping steam_app_id to hltb_game_id.
        """
        cutoff = int(time.time()) - (self._HLTB_CACHE_TTL_DAYS * 86400)
        cursor = self.conn.execute(
            "SELECT steam_app_id, hltb_game_id FROM hltb_id_cache WHERE cached_at > ?",
            (cutoff,),
        )
        return {row[0]: row[1] for row in cursor.fetchall()}

    def save_hltb_id_cache(self, mappings: dict[int, int]) -> int:
        """Saves steam_app_id → hltb_game_id mappings to the cache table.

        Uses INSERT OR REPLACE to update existing entries.

        Args:
            mappings: Dict mapping steam_app_id to hltb_game_id.

        Returns:
            Number of mappings saved.
        """
        if not mappings:
            return 0

        now = int(time.time())
        rows = [(steam_id, hltb_id, now) for steam_id, hltb_id in mappings.items()]
        self.conn.executemany(
            "INSERT OR REPLACE INTO hltb_id_cache (steam_app_id, hltb_game_id, cached_at) VALUES (?, ?, ?)",
            rows,
        )
        self.conn.commit()
        return len(rows)

    def clear_expired_hltb_cache(self) -> int:
        """Removes expired entries from the HLTB ID cache.

        Returns:
            Number of entries removed.
        """
        cutoff = int(time.time()) - (self._HLTB_CACHE_TTL_DAYS * 86400)
        cursor = self.conn.execute("DELETE FROM hltb_id_cache WHERE cached_at <= ?", (cutoff,))
        self.conn.commit()
        return cursor.rowcount

    # ========================================================================
    # PROTONDB OPERATIONS (Phase 6.2)
    # ========================================================================

    _PROTONDB_TTL_DAYS = 7

    def get_cached_protondb(self, app_id: int) -> dict | None:
        """Returns cached ProtonDB rating if fresh enough.

        Args:
            app_id: Steam app ID.

        Returns:
            Dict with tier, confidence, trending_tier, score, best_reported,
            last_updated keys, or None if not cached or expired.
        """
        cutoff = int(time.time()) - (self._PROTONDB_TTL_DAYS * 86400)
        cursor = self.conn.execute(
            "SELECT tier, confidence, trending_tier, score, best_reported, last_updated"
            " FROM protondb_ratings WHERE app_id = ? AND last_updated > ?",
            (app_id, cutoff),
        )
        row = cursor.fetchone()
        if not row:
            return None
        return {
            "tier": row[0],
            "confidence": row[1],
            "trending_tier": row[2],
            "score": float(row[3]),
            "best_reported": row[4],
            "last_updated": int(row[5]),
        }

    def upsert_protondb(
        self,
        app_id: int,
        tier: str,
        confidence: str = "",
        trending_tier: str = "",
        score: float = 0.0,
        best_reported: str = "",
    ) -> None:
        """Inserts or updates a ProtonDB rating.

        Args:
            app_id: Steam app ID.
            tier: Compatibility tier.
            confidence: Confidence level.
            trending_tier: Trending tier direction.
            score: Numeric score.
            best_reported: Best reported tier.
        """
        self.conn.execute(
            """
            INSERT OR REPLACE INTO protondb_ratings
            (app_id, tier, confidence, trending_tier, score, best_reported, last_updated)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (app_id, tier, confidence, trending_tier, score, best_reported, int(time.time())),
        )

    def get_apps_without_protondb(self) -> list[tuple[int, str]]:
        """Returns game-type apps that have no ProtonDB rating.

        Returns:
            List of (app_id, name) tuples for games without ProtonDB data.
        """
        cursor = self.conn.execute("""
            SELECT g.app_id, g.name FROM games g
            LEFT JOIN protondb_ratings p ON g.app_id = p.app_id
            WHERE p.app_id IS NULL AND g.app_type IN ('game', '')
            """)
        return [(row[0], row[1]) for row in cursor.fetchall()]

    def batch_get_protondb(self, app_ids: list[int]) -> dict[int, str]:
        """Batch load ProtonDB tiers for multiple app_ids.

        Args:
            app_ids: List of app IDs.

        Returns:
            Dict mapping app_id to tier string.
        """
        if not app_ids:
            return {}

        placeholders = ",".join("?" * len(app_ids))
        cursor = self.conn.execute(
            f"SELECT app_id, tier FROM protondb_ratings WHERE app_id IN ({placeholders})",
            app_ids,
        )
        return {row[0]: row[1] for row in cursor.fetchall()}

    # ========================================================================
    # HEALTH CHECK QUERIES (MD 05)
    # ========================================================================

    def get_games_missing_artwork(self) -> list[tuple[int, str]]:
        """Returns games that have no custom artwork entry in the database.

        Returns:
            List of (app_id, name) tuples for games without cover images.
        """
        cursor = self.conn.execute("""
            SELECT g.app_id, g.name FROM games g
            LEFT JOIN custom_artwork ca ON g.app_id = ca.app_id
            WHERE ca.app_id IS NULL AND g.app_type IN ('game', '')
        """)
        return [(row[0], row[1]) for row in cursor.fetchall()]

    def get_stale_hltb_count(self, max_age_days: int = 30) -> int:
        """Counts games with HLTB cache older than max_age_days.

        Args:
            max_age_days: Maximum cache age in days.

        Returns:
            Number of games with stale HLTB data.
        """
        cutoff = int(time.time()) - (max_age_days * 86400)
        cursor = self.conn.execute(
            "SELECT COUNT(*) FROM hltb_data WHERE last_updated < ?",
            (cutoff,),
        )
        return cursor.fetchone()[0]

    def get_stale_protondb_count(self, max_age_days: int = 7) -> int:
        """Counts games with ProtonDB cache older than max_age_days.

        Args:
            max_age_days: Maximum cache age in days.

        Returns:
            Number of games with stale ProtonDB data.
        """
        cutoff = int(time.time()) - (max_age_days * 86400)
        cursor = self.conn.execute(
            "SELECT COUNT(*) FROM protondb_ratings WHERE last_updated < ?",
            (cutoff,),
        )
        return cursor.fetchone()[0]

    # ========================================================================
    # ACHIEVEMENT OPERATIONS (Phase 5.2)
    # ========================================================================

    def upsert_achievement_stats(
        self, app_id: int, total: int, unlocked: int, completion_pct: float, perfect: bool
    ) -> None:
        """Inserts or updates achievement statistics for a game.

        Args:
            app_id: Steam app ID.
            total: Total number of achievements.
            unlocked: Number of unlocked achievements.
            completion_pct: Completion percentage (0.0-100.0).
            perfect: Whether all achievements are unlocked.
        """
        self.conn.execute(
            """
            INSERT OR REPLACE INTO achievement_stats
            (app_id, total_achievements, unlocked_achievements, completion_percentage, perfect_game)
            VALUES (?, ?, ?, ?, ?)
            """,
            (app_id, total, unlocked, round(completion_pct, 2), perfect),
        )

    def upsert_achievements(self, app_id: int, achievements: list[dict]) -> None:
        """Batch inserts or updates individual achievements for a game.

        Args:
            app_id: Steam app ID.
            achievements: List of achievement dicts with keys:
                achievement_id, name, description, is_unlocked,
                unlock_time, is_hidden, rarity_percentage.
        """
        if not achievements:
            return

        rows = [
            (
                app_id,
                ach.get("achievement_id", ""),
                ach.get("name", ""),
                ach.get("description", ""),
                ach.get("is_unlocked", False),
                ach.get("unlock_time", 0),
                ach.get("is_hidden", False),
                ach.get("rarity_percentage", 0.0),
            )
            for ach in achievements
        ]
        self.conn.executemany(
            """
            INSERT OR REPLACE INTO achievements
            (app_id, achievement_id, name, description,
             is_unlocked, unlock_time, is_hidden, rarity_percentage)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            rows,
        )

    def get_apps_without_achievements(self) -> list[tuple[int, str]]:
        """Returns game-type apps that have no achievement_stats entry.

        Returns:
            List of (app_id, name) tuples for games without achievement data.
        """
        cursor = self.conn.execute("""
            SELECT g.app_id, g.name FROM games g
            LEFT JOIN achievement_stats a ON g.app_id = a.app_id
            WHERE a.app_id IS NULL AND g.app_type IN ('game', '')
            """)
        return [(row[0], row[1]) for row in cursor.fetchall()]

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

    # ========================================================================
    # SMART COLLECTION OPERATIONS (Phase 5.3)
    # ========================================================================

    def create_smart_collection(self, name: str, description: str, icon: str, rules_json: str) -> int:
        """Creates a new smart collection in the database.

        Args:
            name: Collection name (must be unique).
            description: Optional description.
            icon: Emoji icon.
            rules_json: JSON string with logic and rules.

        Returns:
            The new collection_id.
        """
        import time

        cursor = self.conn.execute(
            """
            INSERT INTO user_collections (name, description, icon, is_smart, rules, created_at)
            VALUES (?, ?, ?, 1, ?, ?)
            """,
            (name, description, icon, rules_json, int(time.time())),
        )
        return cursor.lastrowid or 0

    def update_smart_collection(
        self, collection_id: int, name: str, description: str, icon: str, rules_json: str
    ) -> None:
        """Updates an existing smart collection.

        Args:
            collection_id: The collection to update.
            name: New name.
            description: New description.
            icon: New icon.
            rules_json: New rules JSON string.
        """
        self.conn.execute(
            """
            UPDATE user_collections
            SET name = ?, description = ?, icon = ?, rules = ?
            WHERE collection_id = ? AND is_smart = 1
            """,
            (name, description, icon, rules_json, collection_id),
        )

    def delete_smart_collection(self, collection_id: int) -> None:
        """Deletes a smart collection and its game associations.

        Args:
            collection_id: The collection to delete.
        """
        self.conn.execute(
            "DELETE FROM collection_games WHERE collection_id = ?",
            (collection_id,),
        )
        self.conn.execute(
            "DELETE FROM user_collections WHERE collection_id = ? AND is_smart = 1",
            (collection_id,),
        )

    def get_smart_collection(self, collection_id: int) -> dict | None:
        """Retrieves a single smart collection by ID.

        Args:
            collection_id: The collection to retrieve.

        Returns:
            Dict with collection fields, or None if not found.
        """
        cursor = self.conn.execute(
            "SELECT * FROM user_collections WHERE collection_id = ? AND is_smart = 1",
            (collection_id,),
        )
        row = cursor.fetchone()
        if not row:
            return None
        columns = [desc[0] for desc in cursor.description]
        return dict(zip(columns, row))

    def get_all_smart_collections(self) -> list[dict]:
        """Retrieves all smart collections ordered by name.

        Returns:
            List of dicts with collection fields.
        """
        cursor = self.conn.execute("SELECT * FROM user_collections WHERE is_smart = 1 ORDER BY name")
        columns = [desc[0] for desc in cursor.description]
        return [dict(zip(columns, row)) for row in cursor.fetchall()]

    def get_smart_collection_by_name(self, name: str) -> dict | None:
        """Retrieves a smart collection by name.

        Args:
            name: The collection name.

        Returns:
            Dict with collection fields, or None if not found.
        """
        cursor = self.conn.execute(
            "SELECT * FROM user_collections WHERE name = ? AND is_smart = 1",
            (name,),
        )
        row = cursor.fetchone()
        if not row:
            return None
        columns = [desc[0] for desc in cursor.description]
        return dict(zip(columns, row))

    def populate_smart_collection(self, collection_id: int, app_ids: list[int]) -> int:
        """Replaces the game membership of a smart collection.

        Deletes existing entries and inserts the new set of app_ids.

        Args:
            collection_id: The collection to populate.
            app_ids: List of app IDs that match the collection rules.

        Returns:
            Number of games added.
        """
        import time

        self.conn.execute(
            "DELETE FROM collection_games WHERE collection_id = ?",
            (collection_id,),
        )
        if not app_ids:
            return 0

        now = int(time.time())
        rows = [(collection_id, app_id, now) for app_id in app_ids]
        self.conn.executemany(
            "INSERT OR IGNORE INTO collection_games (collection_id, app_id, added_at) VALUES (?, ?, ?)",
            rows,
        )
        return len(app_ids)

    def get_smart_collection_games(self, collection_id: int) -> list[int]:
        """Retrieves all app IDs in a smart collection.

        Args:
            collection_id: The collection to query.

        Returns:
            List of app IDs.
        """
        cursor = self.conn.execute(
            "SELECT app_id FROM collection_games WHERE collection_id = ?",
            (collection_id,),
        )
        return [row[0] for row in cursor.fetchall()]

    # ========================================================================
    # TAG DEFINITIONS
    # ========================================================================

    def populate_tag_definitions(self, tags: list[tuple[int, str, str]]) -> int:
        """Bulk-insert tag definitions (TagID → localized name).

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
        """Bulk-insert game→tag associations using TagIDs.

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
        """Get total number of game→tag associations.

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

    def bulk_update_review_scores(self, scores: list[tuple[int, int]]) -> int:
        """Batch-update review_score in the games table.

        Args:
            scores: List of (review_score, app_id) tuples.

        Returns:
            Number of rows updated.
        """
        self.conn.executemany(
            "UPDATE games SET review_score = ? WHERE app_id = ?",
            scores,
        )
        return len(scores)

    # ========================================================================
    # UTILITY METHODS
    # ========================================================================

    def commit(self) -> None:
        """Commit current transaction."""
        self.conn.commit()

    def close(self) -> None:
        """Close database connection."""
        self.conn.close()

    def __enter__(self) -> Database:
        """Context manager entry."""
        return self

    def __exit__(self, *args: Any) -> None:
        """Context manager exit."""
        self.commit()
        self.close()
