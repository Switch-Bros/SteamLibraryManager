# tests/unit/test_services/test_achievement_data.py

"""Tests for Achievement data flow: Game dataclass, DatabaseEntry mapping, DB operations."""

from __future__ import annotations

from pathlib import Path

import pytest

from src.core.database import Database, DatabaseEntry, database_entry_to_game
from src.core.game import Game

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def db(tmp_path: Path) -> Database:
    """Returns a fresh Database instance with schema."""
    return Database(tmp_path / "test.db")


def _insert_game(db: Database, app_id: int, name: str = "Test Game", app_type: str = "game") -> None:
    """Helper to insert a minimal game row."""
    import time

    now = int(time.time())
    db.conn.execute(
        "INSERT OR IGNORE INTO games (app_id, name, app_type, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
        (app_id, name, app_type, now, now),
    )
    db.conn.commit()


# ---------------------------------------------------------------------------
# Game dataclass fields
# ---------------------------------------------------------------------------


class TestGameAchievementFields:
    """Tests for achievement fields on the Game dataclass."""

    def test_game_has_achievement_total(self) -> None:
        """Game has achievement_total field with default 0."""
        game = Game(app_id="1", name="Test")
        assert game.achievement_total == 0

    def test_game_has_achievement_unlocked(self) -> None:
        """Game has achievement_unlocked field with default 0."""
        game = Game(app_id="1", name="Test")
        assert game.achievement_unlocked == 0

    def test_game_has_achievement_percentage(self) -> None:
        """Game has achievement_percentage field with default 0.0."""
        game = Game(app_id="1", name="Test")
        assert game.achievement_percentage == 0.0

    def test_game_has_achievement_perfect(self) -> None:
        """Game has achievement_perfect field with default False."""
        game = Game(app_id="1", name="Test")
        assert game.achievement_perfect is False

    def test_game_achievement_fields_settable(self) -> None:
        """Achievement fields can be set via constructor."""
        game = Game(
            app_id="1",
            name="Test",
            achievement_total=50,
            achievement_unlocked=25,
            achievement_percentage=50.0,
            achievement_perfect=False,
        )
        assert game.achievement_total == 50
        assert game.achievement_unlocked == 25
        assert game.achievement_percentage == 50.0
        assert game.achievement_perfect is False

    def test_game_perfect_game(self) -> None:
        """Perfect game has all fields set correctly."""
        game = Game(
            app_id="1",
            name="Perfect",
            achievement_total=30,
            achievement_unlocked=30,
            achievement_percentage=100.0,
            achievement_perfect=True,
        )
        assert game.achievement_perfect is True
        assert game.achievement_percentage == 100.0


# ---------------------------------------------------------------------------
# database_entry_to_game mapping
# ---------------------------------------------------------------------------


class TestDatabaseEntryToGameAchievements:
    """Tests for achievement field mapping in database_entry_to_game."""

    def test_maps_achievement_total(self) -> None:
        """achievements_total maps to achievement_total."""
        entry = DatabaseEntry(app_id=1, name="Test", achievements_total=42)
        game = database_entry_to_game(entry)
        assert game.achievement_total == 42

    def test_maps_achievement_unlocked(self) -> None:
        """achievement_unlocked maps correctly."""
        entry = DatabaseEntry(app_id=1, name="Test", achievement_unlocked=10)
        game = database_entry_to_game(entry)
        assert game.achievement_unlocked == 10

    def test_maps_achievement_percentage(self) -> None:
        """achievement_percentage maps correctly."""
        entry = DatabaseEntry(app_id=1, name="Test", achievement_percentage=75.5)
        game = database_entry_to_game(entry)
        assert game.achievement_percentage == 75.5

    def test_maps_achievement_perfect(self) -> None:
        """achievement_perfect maps correctly."""
        entry = DatabaseEntry(app_id=1, name="Test", achievement_perfect=True)
        game = database_entry_to_game(entry)
        assert game.achievement_perfect is True

    def test_defaults_all_zero(self) -> None:
        """Default DatabaseEntry produces zero achievement values."""
        entry = DatabaseEntry(app_id=1, name="Test")
        game = database_entry_to_game(entry)
        assert game.achievement_total == 0
        assert game.achievement_unlocked == 0
        assert game.achievement_percentage == 0.0
        assert game.achievement_perfect is False


# ---------------------------------------------------------------------------
# DB operations
# ---------------------------------------------------------------------------


class TestUpsertAchievementStats:
    """Tests for Database.upsert_achievement_stats."""

    def test_insert_achievement_stats(self, db: Database) -> None:
        """Inserts achievement stats for a game."""
        _insert_game(db, 100)
        db.upsert_achievement_stats(100, 50, 25, 50.0, False)
        db.commit()

        cursor = db.conn.execute(
            "SELECT total_achievements, unlocked_achievements, completion_percentage, perfect_game"
            " FROM achievement_stats WHERE app_id = ?",
            (100,),
        )
        row = cursor.fetchone()
        assert row is not None
        assert row[0] == 50
        assert row[1] == 25
        assert float(row[2]) == 50.0
        assert bool(row[3]) is False

    def test_update_achievement_stats(self, db: Database) -> None:
        """Updates existing achievement stats (upsert behavior)."""
        _insert_game(db, 100)
        db.upsert_achievement_stats(100, 50, 10, 20.0, False)
        db.upsert_achievement_stats(100, 50, 50, 100.0, True)
        db.commit()

        cursor = db.conn.execute(
            "SELECT unlocked_achievements, completion_percentage, perfect_game FROM achievement_stats WHERE app_id = ?",
            (100,),
        )
        row = cursor.fetchone()
        assert row is not None
        assert row[0] == 50
        assert float(row[1]) == 100.0
        assert bool(row[2]) is True

    def test_stats_with_zero_achievements(self, db: Database) -> None:
        """Games without achievements get stats with total=0."""
        _insert_game(db, 100)
        db.upsert_achievement_stats(100, 0, 0, 0.0, False)
        db.commit()

        cursor = db.conn.execute(
            "SELECT total_achievements FROM achievement_stats WHERE app_id = ?",
            (100,),
        )
        row = cursor.fetchone()
        assert row is not None
        assert row[0] == 0


class TestUpsertAchievements:
    """Tests for Database.upsert_achievements."""

    def test_insert_achievements(self, db: Database) -> None:
        """Inserts individual achievement records."""
        _insert_game(db, 100)
        achievements = [
            {
                "achievement_id": "ACH_001",
                "name": "First Blood",
                "description": "Get your first kill",
                "is_unlocked": True,
                "unlock_time": 1700000000,
                "is_hidden": False,
                "rarity_percentage": 85.5,
            },
            {
                "achievement_id": "ACH_002",
                "name": "Veteran",
                "description": "Win 100 matches",
                "is_unlocked": False,
                "unlock_time": 0,
                "is_hidden": True,
                "rarity_percentage": 5.2,
            },
        ]
        db.upsert_achievements(100, achievements)
        db.commit()

        cursor = db.conn.execute("SELECT COUNT(*) FROM achievements WHERE app_id = ?", (100,))
        assert cursor.fetchone()[0] == 2

    def test_upsert_achievements_empty_list(self, db: Database) -> None:
        """Empty achievement list does nothing."""
        _insert_game(db, 100)
        db.upsert_achievements(100, [])
        db.commit()

        cursor = db.conn.execute("SELECT COUNT(*) FROM achievements WHERE app_id = ?", (100,))
        assert cursor.fetchone()[0] == 0

    def test_upsert_achievements_replaces(self, db: Database) -> None:
        """Upserting same achievement_id replaces existing record."""
        _insert_game(db, 100)
        db.upsert_achievements(
            100,
            [
                {"achievement_id": "ACH_001", "name": "Old", "is_unlocked": False},
            ],
        )
        db.upsert_achievements(
            100,
            [
                {"achievement_id": "ACH_001", "name": "New", "is_unlocked": True},
            ],
        )
        db.commit()

        cursor = db.conn.execute(
            "SELECT name, is_unlocked FROM achievements WHERE app_id = ? AND achievement_id = ?",
            (100, "ACH_001"),
        )
        row = cursor.fetchone()
        assert row[0] == "New"
        assert bool(row[1]) is True


class TestGetAppsWithoutAchievements:
    """Tests for Database.get_apps_without_achievements."""

    def test_returns_games_without_stats(self, db: Database) -> None:
        """Returns games that have no achievement_stats entry."""
        _insert_game(db, 100, "Game A")
        _insert_game(db, 200, "Game B")
        db.upsert_achievement_stats(100, 10, 5, 50.0, False)
        db.commit()

        result = db.get_apps_without_achievements()
        app_ids = [r[0] for r in result]
        assert 200 in app_ids
        assert 100 not in app_ids

    def test_returns_empty_when_all_have_stats(self, db: Database) -> None:
        """Returns empty list when all games have stats."""
        _insert_game(db, 100, "Game A")
        db.upsert_achievement_stats(100, 10, 5, 50.0, False)
        db.commit()

        result = db.get_apps_without_achievements()
        app_ids = [r[0] for r in result]
        assert 100 not in app_ids

    def test_excludes_non_game_types(self, db: Database) -> None:
        """Non-game app types (tool, music) are excluded."""
        _insert_game(db, 300, "Tool App", app_type="tool")
        result = db.get_apps_without_achievements()
        app_ids = [r[0] for r in result]
        assert 300 not in app_ids


class TestBatchGetAchievementStats:
    """Tests for Database._batch_get_achievement_stats."""

    def test_batch_load_multiple(self, db: Database) -> None:
        """Loads stats for multiple app_ids in one query."""
        _insert_game(db, 100)
        _insert_game(db, 200)
        db.upsert_achievement_stats(100, 50, 25, 50.0, False)
        db.upsert_achievement_stats(200, 30, 30, 100.0, True)
        db.commit()

        result = db._batch_get_achievement_stats([100, 200])
        assert 100 in result
        assert 200 in result
        assert result[100] == (50, 25, 50.0, False)
        assert result[200] == (30, 30, 100.0, True)

    def test_batch_load_empty_list(self, db: Database) -> None:
        """Empty app_ids list returns empty dict."""
        result = db._batch_get_achievement_stats([])
        assert result == {}

    def test_batch_load_missing_app(self, db: Database) -> None:
        """App IDs not in achievement_stats are absent from result."""
        _insert_game(db, 100)
        result = db._batch_get_achievement_stats([100])
        assert 100 not in result
