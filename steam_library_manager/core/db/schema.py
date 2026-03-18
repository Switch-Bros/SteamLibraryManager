#
# steam_library_manager/core/db/schema.py
# Schema creation and migration (v3 through v9)
#
# Copyright © 2025-2026 SwitchBros
# Licensed under the MIT License. See LICENSE for details.
#

from __future__ import annotations

import logging
import sqlite3
import time
from pathlib import Path

from steam_library_manager.utils.i18n import t

logger = logging.getLogger("steamlibmgr.database")

__all__ = ["SchemaMixin"]


class SchemaMixin:
    """Schema creation and migration logic.

    Creates schema from schema.sql on first run, then applies
    migrations v3-v9 for existing databases. Each migration is
    idempotent (IF NOT EXISTS, try/except for ALTER TABLE).
    """

    def _ensure_schema(self):
        ver = self._get_schema_version()
        if ver == 0:
            self._create_schema()
            self._set_schema_version(self.SCHEMA_VERSION)
        elif ver < self.SCHEMA_VERSION:
            self._migrate(ver, self.SCHEMA_VERSION)

    def _get_schema_version(self):
        try:
            cur = self.conn.execute("SELECT MAX(version) FROM schema_version")
            r = cur.fetchone()
            return r[0] if r[0] is not None else 0
        except sqlite3.OperationalError:
            return 0

    def _set_schema_version(self, v):
        self.conn.execute(
            "INSERT OR REPLACE INTO schema_version (version, applied_at, description) VALUES (?, ?, ?)",
            (v, int(time.time()), t("logs.db.schema_created")),
        )
        self.conn.commit()

    def _create_schema(self):
        # load schema from sql
        p = Path(__file__).parent / "schema.sql"
        try:
            with open(p) as f:
                sql = f.read()
        except FileNotFoundError:
            logger.error(t("logs.db.schema_not_found", path=str(p)))
            raise

        try:
            self.conn.executescript(sql)
            self.conn.commit()
            logger.info(t("logs.db.schema_created"))
        except sqlite3.Error as e:
            logger.error(t("logs.db.schema_error", error=str(e)))
            raise

    def _migrate(self, frm, to):
        logger.info("Migrating from %d to %d" % (frm, to))

        if frm < 3:
            self._m3()
            self._set_schema_version(3)
        if frm < 4:
            self._m4()
            self._set_schema_version(4)
        if frm < 5:
            self._m5()
            self._set_schema_version(5)
        if frm < 6:
            self._m6()
            self._set_schema_version(6)
        if frm < 7:
            self._m7()
            self._set_schema_version(7)
        if frm < 8:
            self._m8()
            self._set_schema_version(8)
        if frm < 9:
            self._m9()
            self._set_schema_version(9)

    # migrations

    def _m3(self):
        # tag_definitions + tag_id
        try:
            self.conn.execute("ALTER TABLE game_tags ADD COLUMN tag_id INTEGER")
        except sqlite3.OperationalError:
            pass
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
        logger.info("Migrated to v3")

    def _m4(self):
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS hltb_id_cache (
                steam_app_id INTEGER PRIMARY KEY,
                hltb_game_id INTEGER NOT NULL,
                cached_at INTEGER NOT NULL
            )
            """)
        self.conn.commit()
        logger.info("Migrated to v4")

    def _m5(self):
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
        logger.info("Migrated to v5")

    def _m6(self):
        try:
            self.conn.execute("ALTER TABLE games ADD COLUMN review_percentage INTEGER")
        except sqlite3.OperationalError:
            pass
        self.conn.commit()
        logger.info("Migrated to v6")

    def _m7(self):
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
        logger.info("Migrated to v7")

    def _m8(self):
        # big: pegi + user tables
        cs = [
            ("pegi_rating", "TEXT DEFAULT ''"),
            ("esrb_rating", "TEXT DEFAULT ''"),
            ("metacritic_score", "INTEGER DEFAULT 0"),
            ("steam_deck_status", "TEXT DEFAULT ''"),
            ("short_description", "TEXT DEFAULT ''"),
            ("content_descriptors", "TEXT DEFAULT ''"),
        ]
        for n, d in cs:
            try:
                self.conn.execute("ALTER TABLE games ADD COLUMN %s %s" % (n, d))
            except sqlite3.OperationalError:
                pass

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
        logger.info("Migrated to v8")

    def _m9(self):
        self.conn.executescript("""
            CREATE TABLE IF NOT EXISTS curators (
                curator_id    INTEGER PRIMARY KEY,
                name          TEXT NOT NULL,
                url           TEXT NOT NULL DEFAULT '',
                source        TEXT NOT NULL DEFAULT 'manual',
                active        INTEGER NOT NULL DEFAULT 1,
                last_updated  TEXT,
                total_count   INTEGER DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS curator_recommendations (
                curator_id    INTEGER NOT NULL,
                app_id        INTEGER NOT NULL,
                PRIMARY KEY (curator_id, app_id),
                FOREIGN KEY (curator_id) REFERENCES curators(curator_id)
                    ON DELETE CASCADE
            );

            CREATE INDEX IF NOT EXISTS idx_curator_rec_app
                ON curator_recommendations(app_id);
        """)
        self.conn.commit()
        logger.info("Migrated to v9")
