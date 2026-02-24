"""Tests for curator overlap score computation (Phase C)."""

from __future__ import annotations

import time
from pathlib import Path

import pytest

from src.core.database import Database
from src.core.game import Game


@pytest.fixture
def db(tmp_path: Path) -> Database:
    """Creates a Database with test games for FK constraints."""
    db_path = tmp_path / "test_curator_overlap.db"
    database = Database(db_path)
    now = int(time.time())
    for app_id in (100, 200, 300, 400):
        database.conn.execute(
            "INSERT OR IGNORE INTO games (app_id, name, app_type, created_at, updated_at) " "VALUES (?, ?, ?, ?, ?)",
            (app_id, f"Game {app_id}", "game", now, now),
        )
    database.commit()
    return database


class TestCuratorOverlapScore:
    """Tests for get_curator_overlap_score() and cache-based computation."""

    def test_no_curators_returns_zero_zero(self, db: Database) -> None:
        """With no curators, overlap should be (0, 0)."""
        recommending, total = db.get_curator_overlap_score(100)
        assert recommending == 0
        assert total == 0

    def test_single_curator_recommends(self, db: Database) -> None:
        """Game recommended by 1 of 1 active curator."""
        db.add_curator(1850, "PC Gamer")
        db.save_curator_recommendations(1850, [100, 200])

        recommending, total = db.get_curator_overlap_score(100)
        assert recommending == 1
        assert total == 1

    def test_game_not_recommended(self, db: Database) -> None:
        """Game not recommended by any curator."""
        db.add_curator(1850, "PC Gamer")
        db.save_curator_recommendations(1850, [200])

        recommending, total = db.get_curator_overlap_score(100)
        assert recommending == 0
        assert total == 1

    def test_multiple_curators_overlap(self, db: Database) -> None:
        """Game recommended by 2 of 3 active curators."""
        db.add_curator(1850, "PC Gamer")
        db.add_curator(33526, "Rock Paper Shotgun")
        db.add_curator(6860, "Eurogamer")
        db.save_curator_recommendations(1850, [100, 200])
        db.save_curator_recommendations(33526, [100])
        db.save_curator_recommendations(6860, [300])

        recommending, total = db.get_curator_overlap_score(100)
        assert recommending == 2
        assert total == 3

    def test_inactive_curator_excluded(self, db: Database) -> None:
        """Inactive curators should not count in overlap."""
        db.add_curator(1850, "PC Gamer")
        db.add_curator(33526, "Rock Paper Shotgun")
        db.save_curator_recommendations(1850, [100])
        db.save_curator_recommendations(33526, [100])
        db.toggle_curator_active(33526, False)

        recommending, total = db.get_curator_overlap_score(100)
        assert recommending == 1
        assert total == 1  # Only 1 active curator

    def test_overlap_from_cache(self) -> None:
        """Overlap computed from in-memory cache (no DB)."""
        cache = {
            1850: {100, 200, 300},
            33526: {100, 400},
            6860: {200, 300},
        }
        game = Game(app_id="100", name="Game 100")

        numeric_id = int(game.app_id)
        recommending = sum(1 for recs in cache.values() if numeric_id in recs)
        total = len(cache)

        assert recommending == 2
        assert total == 3
        assert f"{recommending}/{total}" == "2/3"

    def test_overlap_non_numeric_app_id(self) -> None:
        """Non-numeric app_id should result in empty overlap."""
        cache = {1850: {100, 200}}
        game = Game(app_id="not_a_number", name="Bad Game")

        try:
            numeric_id = int(game.app_id)
            recommending = sum(1 for recs in cache.values() if numeric_id in recs)
            overlap = f"{recommending}/{len(cache)}"
        except (ValueError, TypeError):
            overlap = ""

        assert overlap == ""
