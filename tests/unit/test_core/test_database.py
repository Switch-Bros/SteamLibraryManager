"""Unit tests for the Database module.

Tests cover:
- Schema creation
- CRUD operations (insert, get, update, delete)
- Batch insert
- get_all_games (efficient batch loading)
- get_game_count
- DatabaseEntry -> Game conversion
- DatabaseImporter conversion logic
- Edge cases (empty DB, duplicate inserts, invalid data)
"""

from __future__ import annotations

from unittest.mock import MagicMock

from src.core.database import Database, DatabaseEntry, ImportStats, database_entry_to_game
from src.core.database_importer import DatabaseImporter

# ========================================================================
# Database class tests
# ========================================================================


class TestDatabaseSchema:
    """Tests for schema creation and versioning."""

    def test_schema_creation_succeeds(self, database: Database) -> None:
        """Database should create schema on init."""
        version = database._get_schema_version()
        assert version == 8

    def test_game_count_empty_db(self, database: Database) -> None:
        """Empty database should have zero games."""
        assert database.get_game_count() == 0

    def test_get_all_games_empty_db(self, database: Database) -> None:
        """get_all_games on empty DB returns empty list."""
        assert database.get_all_games() == []


class TestDatabaseCRUD:
    """Tests for insert, get, update, delete operations."""

    def test_insert_and_get_game(self, database: Database) -> None:
        """Inserted game should be retrievable."""
        entry = DatabaseEntry(app_id=440, name="Team Fortress 2", app_type="game")
        database.insert_game(entry)
        database.commit()

        result = database.get_game(440)
        assert result is not None
        assert result.app_id == 440
        assert result.name == "Team Fortress 2"
        assert result.app_type == "game"

    def test_get_nonexistent_game_returns_none(self, database: Database) -> None:
        """get_game for missing app_id returns None."""
        assert database.get_game(999999) is None

    def test_insert_game_with_genres(self, database: Database) -> None:
        """Genres should be stored and loaded correctly."""
        entry = DatabaseEntry(
            app_id=440,
            name="TF2",
            genres=["Action", "Free to Play"],
        )
        database.insert_game(entry)
        database.commit()

        result = database.get_game(440)
        assert result is not None
        assert set(result.genres) == {"Action", "Free to Play"}

    def test_insert_game_with_tags(self, database: Database) -> None:
        """Tags should be stored and loaded correctly."""
        entry = DatabaseEntry(
            app_id=730,
            name="CS2",
            tags=["Competitive", "Shooter", "FPS"],
        )
        database.insert_game(entry)
        database.commit()

        result = database.get_game(730)
        assert result is not None
        assert set(result.tags) == {"Competitive", "Shooter", "FPS"}

    def test_insert_game_with_languages(self, database: Database) -> None:
        """Language data should be stored and loaded correctly."""
        entry = DatabaseEntry(
            app_id=440,
            name="TF2",
            languages={
                "english": {"interface": True, "audio": True, "subtitles": True},
                "german": {"interface": True, "audio": False, "subtitles": True},
            },
        )
        database.insert_game(entry)
        database.commit()

        result = database.get_game(440)
        assert result is not None
        assert "english" in result.languages
        assert result.languages["english"]["audio"] is True
        assert result.languages["german"]["audio"] is False

    def test_update_game_preserves_data(self, database: Database) -> None:
        """update_game should change fields without losing created_at."""
        entry = DatabaseEntry(app_id=440, name="TF2", developer="Valve")
        database.insert_game(entry)
        database.commit()

        # Fetch created_at
        row = database.conn.execute("SELECT created_at FROM games WHERE app_id = 440").fetchone()
        original_created = row[0]

        # Update
        updated_entry = DatabaseEntry(app_id=440, name="Team Fortress 2", developer="Valve Corporation")
        database.update_game(updated_entry)
        database.commit()

        # Verify updated data
        result = database.get_game(440)
        assert result is not None
        assert result.name == "Team Fortress 2"
        assert result.developer == "Valve Corporation"

        # Verify created_at was preserved
        row = database.conn.execute("SELECT created_at FROM games WHERE app_id = 440").fetchone()
        assert row[0] == original_created

    def test_delete_game(self, database: Database) -> None:
        """delete_game should remove the game and its related data."""
        entry = DatabaseEntry(app_id=440, name="TF2", genres=["Action"], tags=["FPS"])
        database.insert_game(entry)
        database.commit()

        database.delete_game(440)
        database.commit()

        assert database.get_game(440) is None
        assert database.get_game_count() == 0

    def test_insert_or_replace_overwrites(self, database: Database) -> None:
        """Inserting a game with the same app_id replaces it."""
        entry1 = DatabaseEntry(app_id=440, name="Old Name")
        database.insert_game(entry1)
        database.commit()

        entry2 = DatabaseEntry(app_id=440, name="New Name")
        database.insert_game(entry2)
        database.commit()

        result = database.get_game(440)
        assert result is not None
        assert result.name == "New Name"
        assert database.get_game_count() == 1


class TestDatabaseBatch:
    """Tests for batch operations."""

    def test_batch_insert_games(self, database: Database, sample_database_entries: list[DatabaseEntry]) -> None:
        """batch_insert_games should insert multiple games in one transaction."""
        count = database.batch_insert_games(sample_database_entries)

        assert count == 3
        assert database.get_game_count() == 3

    def test_batch_insert_empty_list(self, database: Database) -> None:
        """batch_insert_games with empty list returns 0."""
        count = database.batch_insert_games([])
        assert count == 0

    def test_get_all_games_returns_all(self, database: Database, sample_database_entries: list[DatabaseEntry]) -> None:
        """get_all_games should return all inserted games with related data."""
        database.batch_insert_games(sample_database_entries)

        games = database.get_all_games()
        assert len(games) == 3

        # Verify genres are loaded
        tf2 = next(g for g in games if g.app_id == 440)
        assert "Action" in tf2.genres
        assert "Free to Play" in tf2.genres

        # Verify tags are loaded
        cs2 = next(g for g in games if g.app_id == 730)
        assert "Competitive" in cs2.tags

    def test_get_all_games_filtered_by_type(
        self, database: Database, sample_database_entries: list[DatabaseEntry]
    ) -> None:
        """get_all_games with type filter should only return matching types."""
        # Add a non-game entry
        entries = list(sample_database_entries) + [DatabaseEntry(app_id=999, name="Soundtrack", app_type="music")]
        database.batch_insert_games(entries)

        games = database.get_all_games(game_types={"game"})
        assert len(games) == 3
        assert all(g.app_type == "game" for g in games)


class TestImportStats:
    """Tests for import recording."""

    def test_record_import(self, database: Database) -> None:
        """record_import should store stats in import_history."""
        stats = ImportStats(
            games_imported=100,
            games_updated=5,
            games_failed=2,
            duration_seconds=15.5,
            source="appinfo.vdf",
        )
        database.record_import(stats)

        cursor = database.conn.execute("SELECT * FROM import_history")
        rows = cursor.fetchall()
        assert len(rows) == 1
        assert rows[0]["games_imported"] == 100
        assert rows[0]["source"] == "appinfo.vdf"


# ========================================================================
# DatabaseEntry -> Game conversion tests
# ========================================================================


class TestDatabaseEntryToGame:
    """Tests for the database_entry_to_game conversion function."""

    def test_basic_conversion(self) -> None:
        """Basic fields should convert correctly."""
        entry = DatabaseEntry(
            app_id=440,
            name="Team Fortress 2",
            app_type="game",
            developer="Valve",
            publisher="Valve",
        )
        game = database_entry_to_game(entry)

        assert game.app_id == "440"
        assert game.name == "Team Fortress 2"
        assert game.app_type == "game"
        assert game.developer == "Valve"
        assert game.publisher == "Valve"

    def test_release_year_from_timestamp(self) -> None:
        """Release year should be extracted from UNIX timestamp."""
        entry = DatabaseEntry(
            app_id=570,
            name="Dota 2",
            release_date=1373328000,  # 2013-07-09
        )
        game = database_entry_to_game(entry)
        assert game.release_year == "2013"

    def test_none_fields_become_empty_strings(self) -> None:
        """None values should convert to empty strings."""
        entry = DatabaseEntry(
            app_id=1,
            name="Test",
            developer=None,
            publisher=None,
            review_score=None,
        )
        game = database_entry_to_game(entry)
        assert game.developer == ""
        assert game.publisher == ""
        assert game.review_score == ""

    def test_sort_name_fallback(self) -> None:
        """sort_name should fall back to name if sort_as is None."""
        entry = DatabaseEntry(app_id=1, name="The Game", sort_as=None)
        game = database_entry_to_game(entry)
        assert game.sort_name == "The Game"

        entry2 = DatabaseEntry(app_id=2, name="The Game", sort_as="Game, The")
        game2 = database_entry_to_game(entry2)
        assert game2.sort_name == "Game, The"

    def test_genres_and_tags_copied(self) -> None:
        """Genres and tags should be copied (not shared reference)."""
        entry = DatabaseEntry(
            app_id=1,
            name="Test",
            genres=["Action"],
            tags=["Indie"],
        )
        game = database_entry_to_game(entry)
        assert game.genres == ["Action"]
        assert game.tags == ["Indie"]

        # Verify they are copies
        game.genres.append("RPG")
        assert "RPG" not in entry.genres

    def test_no_release_date_gives_empty_year(self) -> None:
        """Missing release date should produce empty release_year."""
        entry = DatabaseEntry(app_id=1, name="Test")
        game = database_entry_to_game(entry)
        assert game.release_year == ""


# ========================================================================
# DatabaseImporter tests
# ========================================================================


class TestDatabaseImporter:
    """Tests for the DatabaseImporter class."""

    def test_needs_initial_import_on_empty_db(self, database: Database) -> None:
        """needs_initial_import should return True for empty DB."""
        mock_appinfo = MagicMock()
        importer = DatabaseImporter(database, mock_appinfo)
        assert importer.needs_initial_import() is True

    def test_needs_initial_import_false_after_insert(self, database: Database) -> None:
        """needs_initial_import should return False after inserting games."""
        entry = DatabaseEntry(app_id=1, name="Test")
        database.insert_game(entry)
        database.commit()

        mock_appinfo = MagicMock()
        importer = DatabaseImporter(database, mock_appinfo)
        assert importer.needs_initial_import() is False

    def test_extract_associations_developer(self) -> None:
        """extract_associations should extract developer names."""
        from src.core.appinfo_manager import extract_associations

        associations = {
            "0": {"type": "developer", "name": "Valve"},
            "1": {"type": "publisher", "name": "Valve Corporation"},
        }
        result = extract_associations(associations, "developer")
        assert result == ["Valve"]

    def test_extract_associations_empty(self) -> None:
        """extract_associations returns empty list when no associations."""
        from src.core.appinfo_manager import extract_associations

        assert extract_associations({}, "developer") == []

    def test_extract_genres_dict_with_description(self) -> None:
        """_extract_genres should handle dict values with description key."""
        common = {
            "genres": {
                "0": {"description": "Action"},
                "1": {"description": "Adventure"},
            }
        }
        genres = DatabaseImporter._extract_genres(common)
        assert genres == ["Action", "Adventure"]

    def test_extract_genres_string_values(self) -> None:
        """_extract_genres should handle direct string values."""
        common = {"genres": {"0": "Action", "1": "RPG"}}
        genres = DatabaseImporter._extract_genres(common)
        assert genres == ["Action", "RPG"]

    def test_extract_genres_empty(self) -> None:
        """_extract_genres returns empty list for missing genres."""
        assert DatabaseImporter._extract_genres({}) == []

    def test_extract_platforms(self) -> None:
        """_extract_platforms should parse oslist correctly."""
        common = {"oslist": "windows,linux,macos"}
        platforms = DatabaseImporter._extract_platforms(common)
        assert "windows" in platforms
        assert "linux" in platforms

    def test_extract_platforms_empty(self) -> None:
        """_extract_platforms returns empty list for missing oslist."""
        assert DatabaseImporter._extract_platforms({}) == []

    def test_parse_release_date_int(self) -> None:
        """_parse_release_date should handle integer timestamps."""
        common = {"steam_release_date": 1373328000}
        assert DatabaseImporter._parse_release_date(common) == 1373328000

    def test_parse_release_date_string(self) -> None:
        """_parse_release_date should handle string timestamps."""
        common = {"steam_release_date": "1373328000"}
        assert DatabaseImporter._parse_release_date(common) == 1373328000

    def test_parse_release_date_none(self) -> None:
        """_parse_release_date returns None when no date available."""
        assert DatabaseImporter._parse_release_date({}) is None

    def test_convert_to_database_entry(self, database: Database) -> None:
        """_convert_to_database_entry should produce a valid DatabaseEntry."""
        mock_appinfo = MagicMock()
        mock_appinfo._find_common_section.return_value = {
            "name": "Test Game",
            "type": "game",
            "oslist": "windows,linux",
            "associations": {
                "0": {"type": "developer", "name": "TestDev"},
                "1": {"type": "publisher", "name": "TestPub"},
            },
            "steam_release_date": 1609459200,
            "genres": {"0": {"description": "Action"}},
        }

        importer = DatabaseImporter(database, mock_appinfo)
        entry = importer._convert_to_database_entry(12345, {"data": {}})

        assert entry.app_id == 12345
        assert entry.name == "Test Game"
        assert entry.developer == "TestDev"
        assert entry.publisher == "TestPub"
        assert entry.release_date == 1609459200
        assert "Action" in entry.genres
        assert "windows" in entry.platforms
        assert "linux" in entry.platforms

    def test_import_from_appinfo_full_flow(self, database: Database) -> None:
        """Full import flow should populate database from mock appinfo."""
        mock_appinfo = MagicMock()
        mock_appinfo.steam_apps = {
            440: {"data": {"common": {"name": "TF2", "type": "game"}}},
            570: {"data": {"common": {"name": "Dota 2", "type": "game"}}},
        }
        mock_appinfo._find_common_section.side_effect = lambda data: data.get("common", {})

        importer = DatabaseImporter(database, mock_appinfo)
        stats = importer.import_from_appinfo()

        assert stats.games_imported == 2
        assert stats.games_failed == 0
        assert database.get_game_count() == 2


# ========================================================================
# get_app_type_lookup tests
# ========================================================================


class TestGetAppTypeLookup:
    """Tests for Database.get_app_type_lookup."""

    def test_get_app_type_lookup(self, database: Database, sample_database_entries) -> None:
        """get_app_type_lookup returns correct app_type and name tuples."""
        database.batch_insert_games(sample_database_entries)

        lookup = database.get_app_type_lookup()

        assert "440" in lookup
        assert lookup["440"] == ("game", "Team Fortress 2")
        assert "570" in lookup
        assert lookup["570"] == ("game", "Dota 2")
        assert "730" in lookup
        assert lookup["730"] == ("game", "Counter-Strike 2")

    def test_get_app_type_lookup_empty(self, database: Database) -> None:
        """get_app_type_lookup on empty DB returns empty dict."""
        lookup = database.get_app_type_lookup()
        assert lookup == {}
