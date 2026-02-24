"""Tests for DB-backed categorize_by_curator in AutoCategorizeService."""

from __future__ import annotations

import time
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from src.core.database import Database
from src.core.game import Game
from src.services.autocategorize_service import AutoCategorizeService


@pytest.fixture
def db(tmp_path: Path) -> Database:
    """Creates a Database with test games for curator tests."""
    db_path = tmp_path / "test_autocat.db"
    database = Database(db_path)
    now = int(time.time())
    for app_id in (100, 200, 300, 400, 500):
        database.conn.execute(
            "INSERT OR IGNORE INTO games (app_id, name, app_type, created_at, updated_at) " "VALUES (?, ?, ?, ?, ?)",
            (app_id, f"Game {app_id}", "game", now, now),
        )
    database.commit()
    return database


@pytest.fixture
def games() -> list[Game]:
    """Sample Game objects matching the DB test games."""
    return [
        Game(app_id="100", name="Game 100"),
        Game(app_id="200", name="Game 200"),
        Game(app_id="300", name="Game 300"),
        Game(app_id="400", name="Game 400"),
        Game(app_id="500", name="Game 500"),
    ]


@pytest.fixture
def service() -> AutoCategorizeService:
    """Creates an AutoCategorizeService with mock dependencies."""
    game_manager = MagicMock()
    category_service = MagicMock()
    return AutoCategorizeService(game_manager, category_service)


class TestCuratorAutocat:
    """Tests for the DB-backed categorize_by_curator method."""

    def test_no_db_path_returns_zero(self, service: AutoCategorizeService, games: list[Game]) -> None:
        """categorize_by_curator should return 0 when no db_path is given."""
        result = service.categorize_by_curator(games, db_path=None)
        assert result == 0

    def test_no_curators_returns_zero(self, service: AutoCategorizeService, db: Database, games: list[Game]) -> None:
        """categorize_by_curator should return 0 when no curators exist."""
        result = service.categorize_by_curator(games, db_path=db.db_path)
        assert result == 0

    def test_curator_with_recommendations(
        self, service: AutoCategorizeService, db: Database, games: list[Game]
    ) -> None:
        """categorize_by_curator should create categories for recommended games."""
        db.add_curator(1850, "PC Gamer")
        db.save_curator_recommendations(1850, [100, 200])

        result = service.categorize_by_curator(games, db_path=db.db_path)
        assert result == 2

    def test_inactive_curator_ignored(self, service: AutoCategorizeService, db: Database, games: list[Game]) -> None:
        """Inactive curators should be skipped."""
        db.add_curator(1850, "PC Gamer")
        db.save_curator_recommendations(1850, [100, 200])
        db.toggle_curator_active(1850, False)

        result = service.categorize_by_curator(games, db_path=db.db_path)
        assert result == 0

    def test_multiple_curators_create_separate_collections(
        self, service: AutoCategorizeService, db: Database, games: list[Game]
    ) -> None:
        """Each active curator should create its own collection."""
        db.add_curator(1850, "PC Gamer")
        db.add_curator(33526, "Rock Paper Shotgun")
        db.save_curator_recommendations(1850, [100])
        db.save_curator_recommendations(33526, [100, 200])

        result = service.categorize_by_curator(games, db_path=db.db_path)
        # PC Gamer: Game 100, RPS: Game 100 + Game 200
        assert result == 3

    def test_empty_recommendations_skipped(
        self, service: AutoCategorizeService, db: Database, games: list[Game]
    ) -> None:
        """Curators with no recommendations should be skipped."""
        db.add_curator(1850, "PC Gamer")
        # No recommendations saved

        result = service.categorize_by_curator(games, db_path=db.db_path)
        assert result == 0

    def test_progress_callback_called(self, service: AutoCategorizeService, db: Database, games: list[Game]) -> None:
        """Progress callback should be called during processing."""
        db.add_curator(1850, "PC Gamer")
        db.save_curator_recommendations(1850, [100])

        calls: list[tuple[int, str]] = []
        service.categorize_by_curator(
            games, db_path=db.db_path, progress_callback=lambda i, name: calls.append((i, name))
        )
        assert len(calls) > 0

    def test_non_numeric_app_id_skipped(self, service: AutoCategorizeService, db: Database) -> None:
        """Games with non-numeric app_ids should be silently skipped."""
        db.add_curator(1850, "PC Gamer")
        db.save_curator_recommendations(1850, [100])

        bad_games = [Game(app_id="not_a_number", name="Bad Game")]
        result = service.categorize_by_curator(bad_games, db_path=db.db_path)
        assert result == 0
