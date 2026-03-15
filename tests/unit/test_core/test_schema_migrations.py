"""Tests for database schema migrations (v3 through v9).

Verifies that each migration step creates the expected tables/columns
and that data survives the full migration chain.
"""

from __future__ import annotations

import sqlite3
import time

from steam_library_manager.core.db.schema import SchemaMixin

# Minimal v2 schema: base tables without any migration additions.
# game_tags has NO tag_id column, games has NO review_percentage/pegi columns.
_V2_BASE_SCHEMA = """
CREATE TABLE IF NOT EXISTS games (
    app_id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    sort_as TEXT,
    app_type TEXT NOT NULL,
    developer TEXT,
    publisher TEXT,
    release_date INTEGER,
    review_score INTEGER,
    review_count INTEGER,
    is_free BOOLEAN DEFAULT 0,
    platforms TEXT,
    is_modified BOOLEAN DEFAULT 0,
    last_updated INTEGER,
    created_at INTEGER NOT NULL,
    updated_at INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS game_genres (
    app_id INTEGER NOT NULL,
    genre TEXT NOT NULL,
    PRIMARY KEY (app_id, genre)
);

CREATE TABLE IF NOT EXISTS game_tags (
    app_id INTEGER NOT NULL,
    tag TEXT NOT NULL,
    PRIMARY KEY (app_id, tag)
);

CREATE TABLE IF NOT EXISTS schema_version (
    version INTEGER PRIMARY KEY,
    applied_at INTEGER NOT NULL,
    description TEXT
);

INSERT INTO schema_version (version, applied_at, description)
VALUES (2, strftime('%s', 'now'), 'v2 base');
"""

SCHEMA_VERSION = 9


class _MigrationHost(SchemaMixin):
    """Minimal host for SchemaMixin so we can call migration methods directly."""

    SCHEMA_VERSION = SCHEMA_VERSION

    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn


def _create_v2_db(tmp_path) -> sqlite3.Connection:
    """Create a fresh SQLite DB at schema v2."""
    db_path = tmp_path / "migrate_test.db"
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.executescript(_V2_BASE_SCHEMA)
    return conn


def _table_exists(conn: sqlite3.Connection, table: str) -> bool:
    row = conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)).fetchone()
    return row is not None


def _column_exists(conn: sqlite3.Connection, table: str, column: str) -> bool:
    cursor = conn.execute(f"PRAGMA table_info({table})")
    return any(row[1] == column for row in cursor.fetchall())


def _index_exists(conn: sqlite3.Connection, index: str) -> bool:
    row = conn.execute("SELECT 1 FROM sqlite_master WHERE type='index' AND name=?", (index,)).fetchone()
    return row is not None


# -- Individual migration tests --


class TestMigrateToV3:
    """v3: tag_definitions table + tag_id column on game_tags."""

    def test_creates_tag_definitions_table(self, tmp_path):
        conn = _create_v2_db(tmp_path)
        host = _MigrationHost(conn)
        host._migrate_to_v3()

        assert _table_exists(conn, "tag_definitions")
        assert _column_exists(conn, "tag_definitions", "tag_id")
        assert _column_exists(conn, "tag_definitions", "language")
        assert _column_exists(conn, "tag_definitions", "name")
        conn.close()

    def test_adds_tag_id_column(self, tmp_path):
        conn = _create_v2_db(tmp_path)
        host = _MigrationHost(conn)
        host._migrate_to_v3()

        assert _column_exists(conn, "game_tags", "tag_id")
        conn.close()

    def test_creates_indexes(self, tmp_path):
        conn = _create_v2_db(tmp_path)
        host = _MigrationHost(conn)
        host._migrate_to_v3()

        assert _index_exists(conn, "idx_tags_tag_id")
        assert _index_exists(conn, "idx_tag_definitions_name")
        assert _index_exists(conn, "idx_tag_definitions_lang")
        conn.close()

    def test_idempotent(self, tmp_path):
        """Running v3 migration twice should not fail."""
        conn = _create_v2_db(tmp_path)
        host = _MigrationHost(conn)
        host._migrate_to_v3()
        host._migrate_to_v3()  # no error
        conn.close()


class TestMigrateToV4:
    """v4: hltb_id_cache table."""

    def test_creates_hltb_id_cache(self, tmp_path):
        conn = _create_v2_db(tmp_path)
        host = _MigrationHost(conn)
        host._migrate_to_v4()

        assert _table_exists(conn, "hltb_id_cache")
        assert _column_exists(conn, "hltb_id_cache", "steam_app_id")
        assert _column_exists(conn, "hltb_id_cache", "hltb_game_id")
        assert _column_exists(conn, "hltb_id_cache", "cached_at")
        conn.close()


class TestMigrateToV5:
    """v5: protondb_ratings table."""

    def test_creates_protondb_ratings(self, tmp_path):
        conn = _create_v2_db(tmp_path)
        host = _MigrationHost(conn)
        host._migrate_to_v5()

        assert _table_exists(conn, "protondb_ratings")
        for col in ("app_id", "tier", "confidence", "trending_tier", "score", "best_reported", "last_updated"):
            assert _column_exists(conn, "protondb_ratings", col)
        conn.close()


class TestMigrateToV6:
    """v6: review_percentage column in games table."""

    def test_adds_review_percentage(self, tmp_path):
        conn = _create_v2_db(tmp_path)
        host = _MigrationHost(conn)
        host._migrate_to_v6()

        assert _column_exists(conn, "games", "review_percentage")
        conn.close()

    def test_preserves_existing_data(self, tmp_path):
        conn = _create_v2_db(tmp_path)
        now = int(time.time())
        conn.execute(
            "INSERT INTO games (app_id, name, app_type, created_at, updated_at) VALUES (440, 'TF2', 'game', ?, ?)",
            (now, now),
        )
        conn.commit()

        host = _MigrationHost(conn)
        host._migrate_to_v6()

        row = conn.execute("SELECT name, review_percentage FROM games WHERE app_id = 440").fetchone()
        assert row[0] == "TF2"
        assert row[1] is None  # new column defaults to NULL
        conn.close()

    def test_idempotent(self, tmp_path):
        conn = _create_v2_db(tmp_path)
        host = _MigrationHost(conn)
        host._migrate_to_v6()
        host._migrate_to_v6()  # no error
        conn.close()


class TestMigrateToV7:
    """v7: external_games table."""

    def test_creates_external_games(self, tmp_path):
        conn = _create_v2_db(tmp_path)
        host = _MigrationHost(conn)
        host._migrate_to_v7()

        assert _table_exists(conn, "external_games")
        for col in ("platform", "platform_app_id", "name", "install_path", "launch_command"):
            assert _column_exists(conn, "external_games", col)
        conn.close()

    def test_creates_indexes(self, tmp_path):
        conn = _create_v2_db(tmp_path)
        host = _MigrationHost(conn)
        host._migrate_to_v7()

        assert _index_exists(conn, "idx_external_platform")
        assert _index_exists(conn, "idx_external_name")
        conn.close()


class TestMigrateToV8:
    """v8: PEGI + user data normalization + future tables."""

    def test_adds_game_columns(self, tmp_path):
        conn = _create_v2_db(tmp_path)
        host = _MigrationHost(conn)
        host._migrate_to_v8()

        for col in (
            "pegi_rating",
            "esrb_rating",
            "metacritic_score",
            "steam_deck_status",
            "short_description",
            "content_descriptors",
        ):
            assert _column_exists(conn, "games", col), f"Missing column: {col}"
        conn.close()

    def test_creates_user_tables(self, tmp_path):
        conn = _create_v2_db(tmp_path)
        host = _MigrationHost(conn)
        host._migrate_to_v8()

        for table in (
            "user_game_status",
            "age_ratings",
            "purchase_history",
            "user_tags",
            "user_game_tags",
            "user_lists",
            "user_list_items",
            "playtime_snapshots",
        ):
            assert _table_exists(conn, table), f"Missing table: {table}"
        conn.close()

    def test_creates_indexes(self, tmp_path):
        conn = _create_v2_db(tmp_path)
        host = _MigrationHost(conn)
        host._migrate_to_v8()

        assert _index_exists(conn, "idx_games_pegi")
        assert _index_exists(conn, "idx_games_deck")
        assert _index_exists(conn, "idx_games_metacritic")
        assert _index_exists(conn, "idx_ugs_status")
        assert _index_exists(conn, "idx_ugs_priority")
        conn.close()

    def test_preserves_existing_data(self, tmp_path):
        conn = _create_v2_db(tmp_path)
        now = int(time.time())
        conn.execute(
            "INSERT INTO games (app_id, name, app_type, developer, created_at, updated_at) "
            "VALUES (730, 'CS2', 'game', 'Valve', ?, ?)",
            (now, now),
        )
        conn.commit()

        host = _MigrationHost(conn)
        host._migrate_to_v8()

        row = conn.execute("SELECT name, developer, pegi_rating FROM games WHERE app_id = 730").fetchone()
        assert row[0] == "CS2"
        assert row[1] == "Valve"
        assert row[2] == ""  # DEFAULT ''
        conn.close()


class TestMigrateToV9:
    """v9: curator tables."""

    def test_creates_curator_tables(self, tmp_path):
        conn = _create_v2_db(tmp_path)
        host = _MigrationHost(conn)
        host._migrate_to_v9()

        assert _table_exists(conn, "curators")
        assert _table_exists(conn, "curator_recommendations")
        conn.close()

    def test_curator_columns(self, tmp_path):
        conn = _create_v2_db(tmp_path)
        host = _MigrationHost(conn)
        host._migrate_to_v9()

        for col in ("curator_id", "name", "url", "source", "active", "total_count"):
            assert _column_exists(conn, "curators", col)
        conn.close()

    def test_creates_index(self, tmp_path):
        conn = _create_v2_db(tmp_path)
        host = _MigrationHost(conn)
        host._migrate_to_v9()

        assert _index_exists(conn, "idx_curator_rec_app")
        conn.close()


# -- Full migration chain --


class TestFullMigrationChain:
    """Test the complete v2 -> v9 migration path."""

    def test_migrate_v2_to_v9(self, tmp_path):
        """Full chain should reach schema version 9."""
        conn = _create_v2_db(tmp_path)
        host = _MigrationHost(conn)
        host._migrate(from_version=2, to_version=9)

        row = conn.execute("SELECT MAX(version) FROM schema_version").fetchone()
        assert row[0] == 9
        conn.close()

    def test_all_tables_exist_after_chain(self, tmp_path):
        """Every table from v3-v9 should exist after full migration."""
        conn = _create_v2_db(tmp_path)
        host = _MigrationHost(conn)
        host._migrate(from_version=2, to_version=9)

        expected_tables = [
            "tag_definitions",  # v3
            "hltb_id_cache",  # v4
            "protondb_ratings",  # v5
            "external_games",  # v7
            "user_game_status",  # v8
            "age_ratings",  # v8
            "purchase_history",  # v8
            "user_tags",  # v8
            "user_game_tags",  # v8
            "user_lists",  # v8
            "user_list_items",  # v8
            "playtime_snapshots",  # v8
            "curators",  # v9
            "curator_recommendations",  # v9
        ]
        for table in expected_tables:
            assert _table_exists(conn, table), f"Missing table after full migration: {table}"
        conn.close()

    def test_all_columns_exist_after_chain(self, tmp_path):
        """Columns added by migrations should exist after full chain."""
        conn = _create_v2_db(tmp_path)
        host = _MigrationHost(conn)
        host._migrate(from_version=2, to_version=9)

        # v3: tag_id on game_tags
        assert _column_exists(conn, "game_tags", "tag_id")
        # v6: review_percentage on games
        assert _column_exists(conn, "games", "review_percentage")
        # v8: enrichment columns on games
        assert _column_exists(conn, "games", "pegi_rating")
        assert _column_exists(conn, "games", "steam_deck_status")
        conn.close()

    def test_data_survives_migration(self, tmp_path):
        """Games and tags inserted at v2 should survive migration to v9."""
        conn = _create_v2_db(tmp_path)
        now = int(time.time())

        # Insert test data at v2
        conn.execute(
            "INSERT INTO games (app_id, name, app_type, developer, created_at, updated_at) "
            "VALUES (440, 'Team Fortress 2', 'game', 'Valve', ?, ?)",
            (now, now),
        )
        conn.execute("INSERT INTO game_genres (app_id, genre) VALUES (440, 'Action')")
        conn.execute("INSERT INTO game_tags (app_id, tag) VALUES (440, 'FPS')")
        conn.commit()

        # Migrate
        host = _MigrationHost(conn)
        host._migrate(from_version=2, to_version=9)

        # Verify data intact
        game = conn.execute("SELECT name, developer FROM games WHERE app_id = 440").fetchone()
        assert game[0] == "Team Fortress 2"
        assert game[1] == "Valve"

        genre = conn.execute("SELECT genre FROM game_genres WHERE app_id = 440").fetchone()
        assert genre[0] == "Action"

        tag = conn.execute("SELECT tag FROM game_tags WHERE app_id = 440").fetchone()
        assert tag[0] == "FPS"

        # New columns should have defaults
        row = conn.execute("SELECT review_percentage, pegi_rating FROM games WHERE app_id = 440").fetchone()
        assert row[0] is None  # review_percentage has no default
        assert row[1] == ""  # pegi_rating DEFAULT ''
        conn.close()

    def test_partial_migration_v5_to_v9(self, tmp_path):
        """A DB already at v5 should only run migrations v6-v9."""
        conn = _create_v2_db(tmp_path)
        host = _MigrationHost(conn)

        # Manually apply v3-v5 and set version
        host._migrate_to_v3()
        host._set_schema_version(3)
        host._migrate_to_v4()
        host._set_schema_version(4)
        host._migrate_to_v5()
        host._set_schema_version(5)

        # Tables from v3-v5 should exist
        assert _table_exists(conn, "tag_definitions")
        assert _table_exists(conn, "hltb_id_cache")
        assert _table_exists(conn, "protondb_ratings")

        # v7+ should NOT exist yet
        assert not _table_exists(conn, "external_games")
        assert not _table_exists(conn, "curators")

        # Now migrate from v5 to v9 (as _ensure_schema would)
        host._migrate(from_version=5, to_version=9)

        # Everything should exist now
        assert _table_exists(conn, "external_games")
        assert _table_exists(conn, "curators")
        assert _column_exists(conn, "games", "review_percentage")

        row = conn.execute("SELECT MAX(version) FROM schema_version").fetchone()
        assert row[0] == 9
        conn.close()

    def test_ensure_schema_triggers_migration(self, tmp_path):
        """_ensure_schema should detect v2 and migrate to current version."""
        conn = _create_v2_db(tmp_path)
        host = _MigrationHost(conn)
        host._ensure_schema()

        row = conn.execute("SELECT MAX(version) FROM schema_version").fetchone()
        assert row[0] == 9
        assert _table_exists(conn, "curators")
        conn.close()
