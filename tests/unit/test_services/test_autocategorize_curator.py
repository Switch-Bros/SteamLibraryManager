"""Unit tests for AutoCategorizeService.categorize_by_curator (DB-backed).

The old live-fetch curator tests were replaced when categorize_by_curator
was rewritten to use DB-stored recommendations (Phase 8B).

Comprehensive tests live in tests/unit/test_services/test_curator_autocat.py.
This file covers additional edge cases.
"""

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
    """Creates a Database with test games for FK constraints."""
    db_path = tmp_path / "test_autocat_curator.db"
    database = Database(db_path)
    now = int(time.time())
    for app_id in (440, 730, 570):
        database.conn.execute(
            "INSERT OR IGNORE INTO games (app_id, name, app_type, created_at, updated_at) " "VALUES (?, ?, ?, ?, ?)",
            (app_id, f"Game {app_id}", "game", now, now),
        )
    database.commit()
    return database


@pytest.fixture
def games() -> list[Game]:
    """Create a list of test games."""
    g1 = Game(app_id="440", name="Team Fortress 2")
    g1.categories = []
    g2 = Game(app_id="730", name="Counter-Strike 2")
    g2.categories = []
    g3 = Game(app_id="570", name="Dota 2")
    g3.categories = []
    return [g1, g2, g3]


@pytest.fixture
def service() -> AutoCategorizeService:
    """Create AutoCategorizeService instance."""
    return AutoCategorizeService(MagicMock(), MagicMock())


class TestCategorizeByCurator:
    """Tests for DB-backed curator categorization."""

    def test_categorize_by_curator_success(
        self, service: AutoCategorizeService, db: Database, games: list[Game]
    ) -> None:
        """Matching games should be categorized."""
        db.add_curator(123, "Test Curator")
        db.save_curator_recommendations(123, [440, 730])

        count = service.categorize_by_curator(games, db_path=db.db_path)
        assert count == 2

    def test_categorize_by_curator_no_matches(
        self, service: AutoCategorizeService, db: Database, games: list[Game]
    ) -> None:
        """Games not in recommendations should not be categorized."""
        db.add_curator(123, "Test Curator")
        db.save_curator_recommendations(123, [999])

        count = service.categorize_by_curator(games, db_path=db.db_path)
        assert count == 0

    def test_categorize_by_curator_with_progress_callback(
        self, service: AutoCategorizeService, db: Database, games: list[Game]
    ) -> None:
        """Progress callback should be invoked during processing."""
        db.add_curator(123, "Test Curator")
        db.save_curator_recommendations(123, [440])

        calls: list[tuple[int, str]] = []
        service.categorize_by_curator(
            games, db_path=db.db_path, progress_callback=lambda i, name: calls.append((i, name))
        )
        assert len(calls) > 0

    def test_categorize_by_curator_empty_games_list(self, service: AutoCategorizeService, db: Database) -> None:
        """Empty game list should return 0."""
        db.add_curator(123, "Test Curator")
        db.save_curator_recommendations(123, [440])

        count = service.categorize_by_curator([], db_path=db.db_path)
        assert count == 0

    def test_categorize_by_curator_no_db_path(self, service: AutoCategorizeService, games: list[Game]) -> None:
        """No db_path should return 0."""
        count = service.categorize_by_curator(games, db_path=None)
        assert count == 0

    def test_categorize_by_curator_partial_matches(
        self, service: AutoCategorizeService, db: Database, games: list[Game]
    ) -> None:
        """Only matching games should be counted."""
        db.add_curator(123, "Test Curator")
        db.save_curator_recommendations(123, [440])

        count = service.categorize_by_curator(games, db_path=db.db_path)
        assert count == 1
