"""Database schema creation and migrations.

Handles initial schema creation from SQL file and all version
migrations (v3 through v8).
"""

from __future__ import annotations

import logging
import sqlite3
import time
from pathlib import Path

from src.utils.i18n import t

logger = logging.getLogger("steamlibmgr.database")

__all__ = ["SchemaMixin"]


class SchemaMixin:
    """Mixin providing schema creation and migration logic.

    Requires ConnectionBase attributes: conn, SCHEMA_VERSION.
    """

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
        schema_path = Path(__file__).parent / "schema.sql"
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

        if from_version < 6:
            self._migrate_to_v6()
            self._set_schema_version(6)

        if from_version < 7:
            self._migrate_to_v7()
            self._set_schema_version(7)

        if from_version < 8:
            self._migrate_to_v8()
            self._set_schema_version(8)

    def _migrate_to_v3(self) -> None:
        """Migrate to schema v3: tag_definitions table + tag_id column."""
        try:
            self.conn.execute("ALTER TABLE game_tags ADD COLUMN tag_id INTEGER")
        except sqlite3.OperationalError:
            pass  # Column already exists

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

    def _migrate_to_v6(self) -> None:
        """Migrate to schema v6: review_percentage column in games table."""
        try:
            self.conn.execute("ALTER TABLE games ADD COLUMN review_percentage INTEGER")
        except sqlite3.OperationalError:
            pass  # Column already exists
        self.conn.commit()
        logger.info("Migrated to schema v6: review_percentage column")

    def _migrate_to_v7(self) -> None:
        """Migrate to schema v7: external_games table."""
        self.conn.executescript("""
            CREATE TABLE IF NOT EXISTS external_games (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                steam_shortcut_id INTEGER,
                platform TEXT NOT NULL,
                platform_app_id TEXT,
                name TEXT NOT NULL,
                install_path TEXT,
                launch_command TEXT,
                icon_path TEXT,
                added_at INTEGER DEFAULT (strftime('%s', 'now')),
                UNIQUE(platform, platform_app_id)
            );
            CREATE INDEX IF NOT EXISTS idx_external_platform ON external_games(platform);
            CREATE INDEX IF NOT EXISTS idx_external_name ON external_games(name);
        """)
        self.conn.commit()
        logger.info("Migrated to schema v7: external_games table")

    def _migrate_to_v8(self) -> None:
        """Migrate to schema v8: PEGI + user data normalization + future tables."""
        new_columns = [
            ("pegi_rating", "TEXT DEFAULT ''"),
            ("esrb_rating", "TEXT DEFAULT ''"),
            ("metacritic_score", "INTEGER DEFAULT 0"),
            ("steam_deck_status", "TEXT DEFAULT ''"),
            ("short_description", "TEXT DEFAULT ''"),
            ("content_descriptors", "TEXT DEFAULT ''"),
        ]
        for col_name, col_def in new_columns:
            try:
                self.conn.execute(f"ALTER TABLE games ADD COLUMN {col_name} {col_def}")
            except sqlite3.OperationalError:
                pass  # Column already exists

        self.conn.executescript("""
            CREATE INDEX IF NOT EXISTS idx_games_pegi ON games(pegi_rating);
            CREATE INDEX IF NOT EXISTS idx_games_deck ON games(steam_deck_status);
            CREATE INDEX IF NOT EXISTS idx_games_metacritic ON games(metacritic_score);

            CREATE TABLE IF NOT EXISTS user_game_status (
                app_id INTEGER PRIMARY KEY,
                status TEXT DEFAULT 'unplayed',
                priority INTEGER DEFAULT 0,
                personal_rating INTEGER,
                play_count INTEGER DEFAULT 0,
                completion_date INTEGER,
                first_played INTEGER,
                notes TEXT,
                updated_at INTEGER NOT NULL,
                FOREIGN KEY (app_id) REFERENCES games(app_id) ON DELETE CASCADE
            );
            CREATE INDEX IF NOT EXISTS idx_ugs_status ON user_game_status(status);
            CREATE INDEX IF NOT EXISTS idx_ugs_priority ON user_game_status(priority);

            CREATE TABLE IF NOT EXISTS age_ratings (
                app_id INTEGER NOT NULL,
                rating_system TEXT NOT NULL,
                rating_value TEXT NOT NULL,
                descriptors TEXT DEFAULT '',
                source TEXT DEFAULT 'api',
                fetched_at INTEGER,
                PRIMARY KEY (app_id, rating_system),
                FOREIGN KEY (app_id) REFERENCES games(app_id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS purchase_history (
                app_id INTEGER PRIMARY KEY,
                purchase_date INTEGER,
                purchase_price REAL,
                currency TEXT DEFAULT 'EUR',
                purchase_source TEXT,
                bundle_name TEXT,
                notes TEXT,
                FOREIGN KEY (app_id) REFERENCES games(app_id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS user_tags (
                tag_id INTEGER PRIMARY KEY AUTOINCREMENT,
                tag_name TEXT UNIQUE NOT NULL,
                color TEXT,
                icon TEXT
            );

            CREATE TABLE IF NOT EXISTS user_game_tags (
                app_id INTEGER NOT NULL,
                tag_id INTEGER NOT NULL,
                PRIMARY KEY (app_id, tag_id),
                FOREIGN KEY (app_id) REFERENCES games(app_id) ON DELETE CASCADE,
                FOREIGN KEY (tag_id) REFERENCES user_tags(tag_id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS user_lists (
                list_id INTEGER PRIMARY KEY AUTOINCREMENT,
                list_name TEXT NOT NULL,
                list_description TEXT,
                icon TEXT,
                created_at INTEGER NOT NULL,
                updated_at INTEGER NOT NULL
            );

            CREATE TABLE IF NOT EXISTS user_list_items (
                list_id INTEGER NOT NULL,
                app_id INTEGER NOT NULL,
                sort_order INTEGER DEFAULT 0,
                PRIMARY KEY (list_id, app_id),
                FOREIGN KEY (list_id) REFERENCES user_lists(list_id) ON DELETE CASCADE,
                FOREIGN KEY (app_id) REFERENCES games(app_id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS playtime_snapshots (
                app_id INTEGER NOT NULL,
                snapshot_date INTEGER NOT NULL,
                playtime_minutes INTEGER NOT NULL,
                playtime_delta INTEGER DEFAULT 0,
                PRIMARY KEY (app_id, snapshot_date),
                FOREIGN KEY (app_id) REFERENCES games(app_id) ON DELETE CASCADE
            );
        """)
        self.conn.commit()
        logger.info("Migrated to schema v8: PEGI + user data normalization + future tables")
