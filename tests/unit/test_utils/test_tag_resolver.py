# tests/unit/test_utils/test_tag_resolver.py

"""Tests for TagResolver: tag definitions loading and TagID resolution."""

from __future__ import annotations

from pathlib import Path

import pytest

from src.core.database import Database
from src.utils.tag_resolver import GENRE_TAG_IDS, TagResolver

# ---------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------


@pytest.fixture()
def db(tmp_path: Path) -> Database:
    """Creates a fresh in-memory-like database with schema."""
    db_path = tmp_path / "test_tags.db"
    return Database(db_path)


@pytest.fixture()
def resolver(db: Database) -> TagResolver:
    """Creates a TagResolver with a real database."""
    return TagResolver(db)


@pytest.fixture()
def small_tag_dir(tmp_path: Path) -> Path:
    """Creates a small steamtags directory with 2 languages."""
    tags_dir = tmp_path / "steamtags"
    tags_dir.mkdir()

    (tags_dir / "tags_en.txt").write_text(
        "19\tAction\n122\tRPG\n492\tIndie\n9\tStrategy\n",
        encoding="utf-8",
    )
    (tags_dir / "tags_de.txt").write_text(
        "19\tAction\n122\tRollenspiel\n492\tIndie\n9\tStrategie\n",
        encoding="utf-8",
    )
    return tags_dir


# ---------------------------------------------------------------
# Tag Definition Loading Tests
# ---------------------------------------------------------------


class TestTagDefinitionLoading:
    """Tests for loading tag definitions from resource files."""

    def test_parse_tag_file_valid(self, small_tag_dir: Path) -> None:
        """Parsing a valid tag file returns correct tuples."""
        result = TagResolver._parse_tag_file(small_tag_dir / "tags_en.txt", "en")
        assert len(result) == 4
        assert (19, "en", "Action") in result
        assert (122, "en", "RPG") in result

    def test_parse_tag_file_skips_empty_lines(self, tmp_path: Path) -> None:
        """Empty and whitespace-only lines are skipped."""
        tag_file = tmp_path / "tags_test.txt"
        tag_file.write_text("\n  \n19\tAction\n\n", encoding="utf-8")
        result = TagResolver._parse_tag_file(tag_file, "en")
        assert len(result) == 1

    def test_parse_tag_file_skips_invalid_ids(self, tmp_path: Path) -> None:
        """Lines with non-numeric IDs are skipped."""
        tag_file = tmp_path / "tags_test.txt"
        tag_file.write_text("abc\tBroken\n19\tAction\n", encoding="utf-8")
        result = TagResolver._parse_tag_file(tag_file, "en")
        assert len(result) == 1
        assert result[0] == (19, "en", "Action")

    def test_parse_tag_file_skips_no_tab(self, tmp_path: Path) -> None:
        """Lines without a tab separator are skipped."""
        tag_file = tmp_path / "tags_test.txt"
        tag_file.write_text("19 Action\n122\tRPG\n", encoding="utf-8")
        result = TagResolver._parse_tag_file(tag_file, "en")
        assert len(result) == 1

    def test_populate_tag_definitions_inserts_rows(self, db: Database) -> None:
        """populate_tag_definitions inserts rows into the database."""
        tags = [(19, "en", "Action"), (122, "en", "RPG"), (19, "de", "Action")]
        count = db.populate_tag_definitions(tags)
        assert count == 3
        assert db.get_tag_definitions_count() == 3

    def test_populate_tag_definitions_upsert(self, db: Database) -> None:
        """Duplicate (tag_id, language) rows are replaced, not duplicated."""
        db.populate_tag_definitions([(19, "en", "Action")])
        db.populate_tag_definitions([(19, "en", "Action Updated")])
        assert db.get_tag_definitions_count() == 1
        assert db.get_tag_name_by_id(19, "en") == "Action Updated"


# ---------------------------------------------------------------
# Tag Resolution Tests
# ---------------------------------------------------------------


class TestTagResolution:
    """Tests for resolving TagIDs to localized names."""

    def test_resolve_tag_id_english(self, db: Database, resolver: TagResolver) -> None:
        """Resolving a TagID in English returns the correct name."""
        db.populate_tag_definitions([(19, "en", "Action"), (19, "de", "Action")])
        assert resolver.resolve_tag_id(19, "en") == "Action"

    def test_resolve_tag_id_german(self, db: Database, resolver: TagResolver) -> None:
        """Resolving a TagID in German returns the localized name."""
        db.populate_tag_definitions([(122, "en", "RPG"), (122, "de", "Rollenspiel")])
        assert resolver.resolve_tag_id(122, "de") == "Rollenspiel"

    def test_resolve_tag_id_fallback_to_english(self, db: Database, resolver: TagResolver) -> None:
        """If a tag is not available in the target language, fall back to English."""
        db.populate_tag_definitions([(19, "en", "Action")])
        assert resolver.resolve_tag_id(19, "ja") == "Action"

    def test_resolve_tag_id_unknown_returns_none(self, resolver: TagResolver) -> None:
        """Unknown TagID returns None."""
        assert resolver.resolve_tag_id(99999) is None

    def test_resolve_tag_ids_multiple(self, db: Database, resolver: TagResolver) -> None:
        """Resolving multiple TagIDs returns a list of names."""
        db.populate_tag_definitions([(19, "en", "Action"), (122, "en", "RPG"), (492, "en", "Indie")])
        result = resolver.resolve_tag_ids([19, 122, 492], "en")
        assert result == ["Action", "RPG", "Indie"]

    def test_resolve_tag_ids_skips_unknown(self, db: Database, resolver: TagResolver) -> None:
        """Unknown TagIDs are silently skipped in batch resolution."""
        db.populate_tag_definitions([(19, "en", "Action")])
        result = resolver.resolve_tag_ids([19, 99999], "en")
        assert result == ["Action"]


# ---------------------------------------------------------------
# Database Query Tests
# ---------------------------------------------------------------


class TestDatabaseQueries:
    """Tests for tag-related database queries."""

    def test_get_all_tag_names_sorted(self, db: Database) -> None:
        """get_all_tag_names returns alphabetically sorted names."""
        db.populate_tag_definitions([(492, "en", "Indie"), (19, "en", "Action"), (122, "en", "RPG")])
        names = db.get_all_tag_names("en")
        assert names == ["Action", "Indie", "RPG"]

    def test_get_all_tag_names_filters_by_language(self, db: Database) -> None:
        """get_all_tag_names only returns names for the requested language."""
        db.populate_tag_definitions([(19, "en", "Action"), (19, "de", "Action"), (122, "de", "Rollenspiel")])
        en_names = db.get_all_tag_names("en")
        de_names = db.get_all_tag_names("de")
        assert len(en_names) == 1
        assert len(de_names) == 2

    def test_get_tag_id_by_name(self, db: Database) -> None:
        """get_tag_id_by_name returns the correct TagID."""
        db.populate_tag_definitions([(122, "en", "RPG")])
        assert db.get_tag_id_by_name("RPG", "en") == 122

    def test_get_tag_id_by_name_not_found(self, db: Database) -> None:
        """get_tag_id_by_name returns None for unknown names."""
        assert db.get_tag_id_by_name("Unknown", "en") is None

    def test_get_tag_name_by_id(self, db: Database) -> None:
        """get_tag_name_by_id returns the correct name."""
        db.populate_tag_definitions([(9, "de", "Strategie")])
        assert db.get_tag_name_by_id(9, "de") == "Strategie"

    def test_get_tag_name_by_id_not_found(self, db: Database) -> None:
        """get_tag_name_by_id returns None for unknown TagIDs."""
        assert db.get_tag_name_by_id(99999, "en") is None

    def test_bulk_insert_game_tags_by_id(self, db: Database) -> None:
        """bulk_insert_game_tags_by_id inserts game→tag associations."""
        # Need a game in the games table for FK
        db.conn.execute(
            "INSERT INTO games (app_id, name, app_type, created_at, updated_at) VALUES (100, 'Test', 'game', 0, 0)"
        )
        db.conn.commit()

        count = db.bulk_insert_game_tags_by_id([(100, 19, "Action"), (100, 122, "RPG")])
        assert count == 2
        assert db.get_game_tag_count() == 2

    def test_game_tags_have_tag_id(self, db: Database) -> None:
        """game_tags rows inserted with tag_id have it stored correctly."""
        db.conn.execute(
            "INSERT INTO games (app_id, name, app_type, created_at, updated_at) VALUES (100, 'Test', 'game', 0, 0)"
        )
        db.conn.commit()

        db.bulk_insert_game_tags_by_id([(100, 19, "Action")])
        cursor = db.conn.execute("SELECT tag, tag_id FROM game_tags WHERE app_id = 100")
        row = cursor.fetchone()
        assert row[0] == "Action"
        assert row[1] == 19


# ---------------------------------------------------------------
# Ensure Loaded Tests
# ---------------------------------------------------------------


class TestEnsureLoaded:
    """Tests for the ensure_loaded mechanism."""

    def test_ensure_loaded_populates_empty_db(self, db: Database) -> None:
        """ensure_loaded loads tags when database is empty."""
        resolver = TagResolver(db)
        # The real steamtags dir should exist in the project
        if resolver.steamtags_dir.exists():
            count = resolver.ensure_loaded()
            assert count > 0

    def test_ensure_loaded_noop_when_populated(self, db: Database) -> None:
        """ensure_loaded is a no-op when tags already exist."""
        db.populate_tag_definitions([(19, "en", "Action")])
        resolver = TagResolver(db)
        count = resolver.ensure_loaded()
        assert count == 1  # Existing count, not re-loaded


# ---------------------------------------------------------------
# Genre Detection Tests
# ---------------------------------------------------------------


class TestGenreDetection:
    """Tests for genre-related functionality."""

    def test_genre_tag_ids_contains_action(self) -> None:
        """GENRE_TAG_IDS must contain Action (19)."""
        assert 19 in GENRE_TAG_IDS

    def test_genre_tag_ids_contains_strategy(self) -> None:
        """GENRE_TAG_IDS must contain Strategy (9)."""
        assert 9 in GENRE_TAG_IDS

    def test_is_genre_tag_true(self, resolver: TagResolver) -> None:
        """Known genre TagIDs return True."""
        assert resolver.is_genre_tag(19) is True  # Action
        assert resolver.is_genre_tag(122) is True  # RPG

    def test_is_genre_tag_false(self, resolver: TagResolver) -> None:
        """Non-genre TagIDs return False."""
        assert resolver.is_genre_tag(1736) is False  # LEGO (not a genre)

    def test_get_genre_names(self, db: Database, resolver: TagResolver) -> None:
        """get_genre_names returns only genre-level tags."""
        db.populate_tag_definitions(
            [
                (19, "en", "Action"),
                (122, "en", "RPG"),
                (1736, "en", "LEGO"),  # Not a genre
            ]
        )
        genres = resolver.get_genre_names("en")
        assert "Action" in genres
        assert "RPG" in genres
        assert "LEGO" not in genres


# ---------------------------------------------------------------
# Schema Migration Tests
# ---------------------------------------------------------------


class TestSchemaMigration:
    """Tests for schema v3 migration (tag_definitions + tag_id)."""

    def test_tag_definitions_table_exists(self, db: Database) -> None:
        """tag_definitions table must exist after Database init."""
        cursor = db.conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='tag_definitions'")
        assert cursor.fetchone() is not None

    def test_game_tags_has_tag_id_column(self, db: Database) -> None:
        """game_tags table must have a tag_id column."""
        cursor = db.conn.execute("PRAGMA table_info(game_tags)")
        columns = [row[1] for row in cursor.fetchall()]
        assert "tag_id" in columns

    def test_schema_version_is_8(self, db: Database) -> None:
        """Database schema version must be 8."""
        cursor = db.conn.execute("SELECT MAX(version) FROM schema_version")
        version = cursor.fetchone()[0]
        assert version == 8
