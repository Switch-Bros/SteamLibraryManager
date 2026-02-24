"""Tests for CuratorManagementDialog construction and data display."""

from __future__ import annotations

import time
from pathlib import Path

import pytest

from src.core.database import Database


@pytest.fixture
def db(tmp_path: Path) -> Database:
    """Creates a Database with test games for FK constraints."""
    db_path = tmp_path / "test_curator_dialog.db"
    database = Database(db_path)
    now = int(time.time())
    for app_id in (100, 200, 300):
        database.conn.execute(
            "INSERT OR IGNORE INTO games (app_id, name, app_type, created_at, updated_at) " "VALUES (?, ?, ?, ?, ?)",
            (app_id, f"Game {app_id}", "game", now, now),
        )
    database.commit()
    return database


class TestCuratorManagementDialogData:
    """Tests for curator management data operations (no Qt required)."""

    def test_db_operations_for_dialog(self, db: Database) -> None:
        """Verifies the DB operations the dialog relies on."""
        db.add_curator(1850, "PC Gamer", "https://store.steampowered.com/curator/1850/")
        curators = db.get_all_curators()
        assert len(curators) == 1
        assert curators[0]["name"] == "PC Gamer"

    def test_add_preset_curator(self, db: Database) -> None:
        """Adding a curator with source='preset' should work."""
        db.add_curator(1850, "PC Gamer", source="preset")
        curators = db.get_all_curators()
        assert len(curators) == 1
        assert curators[0]["source"] == "preset"

    def test_remove_curator_clears_data(self, db: Database) -> None:
        """Removing a curator should clear recommendations too."""
        db.add_curator(1850, "PC Gamer")
        db.save_curator_recommendations(1850, [100, 200])
        assert len(db.get_recommendations_for_curator(1850)) == 2

        db.remove_curator(1850)
        assert db.get_all_curators() == []
        assert db.get_recommendations_for_curator(1850) == set()

    def test_toggle_active_state(self, db: Database) -> None:
        """Toggling active state should be persisted."""
        db.add_curator(1850, "PC Gamer")
        db.toggle_curator_active(1850, False)
        assert db.get_active_curators() == []

        db.toggle_curator_active(1850, True)
        assert len(db.get_active_curators()) == 1

    def test_multiple_curators_listed(self, db: Database) -> None:
        """get_all_curators should return all curators for the dialog table."""
        db.add_curator(1850, "PC Gamer")
        db.add_curator(33526, "Rock Paper Shotgun")
        db.add_curator(6860, "Eurogamer")

        curators = db.get_all_curators()
        assert len(curators) == 3
        names = {c["name"] for c in curators}
        assert "PC Gamer" in names
        assert "Rock Paper Shotgun" in names
        assert "Eurogamer" in names

    def test_curator_with_recommendations_shows_count(self, db: Database) -> None:
        """total_count should be updated after saving recommendations."""
        db.add_curator(1850, "PC Gamer")
        db.save_curator_recommendations(1850, [100, 200, 300])

        curators = db.get_all_curators()
        assert curators[0]["total_count"] == 3
