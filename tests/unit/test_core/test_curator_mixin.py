"""Tests for CuratorMixin database operations."""

from __future__ import annotations

import time
from pathlib import Path

import pytest

from src.core.database import Database


@pytest.fixture
def db(tmp_path: Path) -> Database:
    """Creates a Database instance with test games for FK constraints."""
    db_path = tmp_path / "test.db"
    database = Database(db_path)
    now = int(time.time())
    for app_id in (100, 200, 300, 400, 500):
        database.conn.execute(
            "INSERT OR IGNORE INTO games (app_id, name, app_type, created_at, updated_at) " "VALUES (?, ?, ?, ?, ?)",
            (app_id, f"Game {app_id}", "game", now, now),
        )
    database.commit()
    return database


class TestCuratorMixin:
    """Tests for CuratorMixin CRUD and query methods."""

    def test_schema_v9_migration(self, db: Database) -> None:
        """Schema version must be 9 after fresh creation."""
        version = db._get_schema_version()
        assert version == 9

    def test_add_curator(self, db: Database) -> None:
        """Adding a curator should persist it."""
        db.add_curator(1850, "PC Gamer", "https://store.steampowered.com/curator/1850/")
        curators = db.get_all_curators()
        assert len(curators) == 1
        assert curators[0]["name"] == "PC Gamer"
        assert curators[0]["curator_id"] == 1850

    def test_add_curator_upsert(self, db: Database) -> None:
        """Adding the same curator again should update name/url."""
        db.add_curator(1850, "PC Gamer", "https://old-url/")
        db.add_curator(1850, "PC Gamer Updated", "https://new-url/")
        curators = db.get_all_curators()
        assert len(curators) == 1
        assert curators[0]["name"] == "PC Gamer Updated"
        assert curators[0]["url"] == "https://new-url/"

    def test_remove_curator_cascades_recommendations(self, db: Database) -> None:
        """Removing a curator should also remove its recommendations."""
        db.add_curator(1850, "PC Gamer")
        db.save_curator_recommendations(1850, [100, 200, 300])
        assert len(db.get_recommendations_for_curator(1850)) == 3

        db.remove_curator(1850)
        assert db.get_all_curators() == []
        assert db.get_recommendations_for_curator(1850) == set()

    def test_save_recommendations_replaces_existing(self, db: Database) -> None:
        """Saving recommendations should replace old ones atomically."""
        db.add_curator(1850, "PC Gamer")
        db.save_curator_recommendations(1850, [100, 200])
        assert db.get_recommendations_for_curator(1850) == {100, 200}

        db.save_curator_recommendations(1850, [300, 400, 500])
        assert db.get_recommendations_for_curator(1850) == {300, 400, 500}

    def test_get_recommendations_returns_set(self, db: Database) -> None:
        """get_recommendations_for_curator should return a set."""
        db.add_curator(1850, "PC Gamer")
        db.save_curator_recommendations(1850, [100, 200])
        result = db.get_recommendations_for_curator(1850)
        assert isinstance(result, set)
        assert result == {100, 200}

    def test_get_curators_for_app(self, db: Database) -> None:
        """Should return all active curators recommending a specific app."""
        db.add_curator(1850, "PC Gamer")
        db.add_curator(33526, "Rock Paper Shotgun")
        db.save_curator_recommendations(1850, [100, 200])
        db.save_curator_recommendations(33526, [100, 300])

        result = db.get_curators_for_app(100)
        names = [name for _, name in result]
        assert "PC Gamer" in names
        assert "Rock Paper Shotgun" in names
        assert len(result) == 2

    def test_overlap_score_calculation(self, db: Database) -> None:
        """Overlap score should count active curators recommending an app."""
        db.add_curator(1, "Curator A")
        db.add_curator(2, "Curator B")
        db.add_curator(3, "Curator C")
        db.save_curator_recommendations(1, [100])
        db.save_curator_recommendations(2, [100])
        db.save_curator_recommendations(3, [200])

        recommending, total = db.get_curator_overlap_score(100)
        assert recommending == 2
        assert total == 3

    def test_overlap_score_no_curators(self, db: Database) -> None:
        """Overlap score should be (0, 0) when no curators exist."""
        recommending, total = db.get_curator_overlap_score(999)
        assert recommending == 0
        assert total == 0

    def test_toggle_active(self, db: Database) -> None:
        """Toggling active should update the flag."""
        db.add_curator(1850, "PC Gamer")
        db.toggle_curator_active(1850, False)
        curators = db.get_all_curators()
        assert curators[0]["active"] == 0

        db.toggle_curator_active(1850, True)
        curators = db.get_all_curators()
        assert curators[0]["active"] == 1

    def test_get_active_curators_excludes_inactive(self, db: Database) -> None:
        """get_active_curators should not return inactive ones."""
        db.add_curator(1, "Active Curator")
        db.add_curator(2, "Inactive Curator")
        db.toggle_curator_active(2, False)

        active = db.get_active_curators()
        assert len(active) == 1
        assert active[0]["name"] == "Active Curator"

    def test_get_curators_needing_refresh_never_updated(self, db: Database) -> None:
        """Curators with last_updated=NULL should need refresh."""
        db.add_curator(1850, "PC Gamer")
        needing = db.get_curators_needing_refresh(max_age_days=7)
        assert len(needing) == 1
        assert needing[0]["curator_id"] == 1850

    def test_save_recommendations_updates_timestamp(self, db: Database) -> None:
        """save_curator_recommendations should set last_updated and total_count."""
        db.add_curator(1850, "PC Gamer")
        db.save_curator_recommendations(1850, [100, 200, 300])

        curators = db.get_all_curators()
        assert curators[0]["total_count"] == 3
        assert curators[0]["last_updated"] is not None
