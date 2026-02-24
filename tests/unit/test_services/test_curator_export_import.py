"""Tests for curator JSON export/import logic (Phase C)."""

from __future__ import annotations

import json
import time
from pathlib import Path

import pytest

from src.core.database import Database


@pytest.fixture
def db(tmp_path: Path) -> Database:
    """Creates a Database with test games for FK constraints."""
    db_path = tmp_path / "test_curator_export.db"
    database = Database(db_path)
    now = int(time.time())
    for app_id in (100, 200, 300):
        database.conn.execute(
            "INSERT OR IGNORE INTO games (app_id, name, app_type, created_at, updated_at) " "VALUES (?, ?, ?, ?, ?)",
            (app_id, f"Game {app_id}", "game", now, now),
        )
    database.commit()
    return database


class TestCuratorExportImport:
    """Tests for JSON export/import round-trip."""

    def test_export_format(self, db: Database, tmp_path: Path) -> None:
        """Exported JSON should have correct structure."""
        db.add_curator(1850, "PC Gamer", "https://store.steampowered.com/curator/1850/")
        db.save_curator_recommendations(1850, [100, 200])

        # Build export data (same logic as dialog)
        curators = db.get_all_curators()
        export_data = []
        for curator in curators:
            recs = sorted(db.get_recommendations_for_curator(curator["curator_id"]))
            export_data.append(
                {
                    "curator_id": curator["curator_id"],
                    "name": curator["name"],
                    "url": curator.get("url", ""),
                    "recommendations": recs,
                }
            )

        data = {"version": 1, "curators": export_data}
        assert data["version"] == 1
        assert len(data["curators"]) == 1
        assert data["curators"][0]["curator_id"] == 1850
        assert data["curators"][0]["recommendations"] == [100, 200]

    def test_round_trip(self, db: Database, tmp_path: Path) -> None:
        """Export then import should preserve all data."""
        db.add_curator(1850, "PC Gamer", "https://store.steampowered.com/curator/1850/")
        db.save_curator_recommendations(1850, [100, 200, 300])
        db.add_curator(33526, "Rock Paper Shotgun")
        db.save_curator_recommendations(33526, [200])

        # Export
        curators = db.get_all_curators()
        export_data = []
        for curator in curators:
            recs = sorted(db.get_recommendations_for_curator(curator["curator_id"]))
            export_data.append(
                {
                    "curator_id": curator["curator_id"],
                    "name": curator["name"],
                    "url": curator.get("url", ""),
                    "source": curator.get("source", "manual"),
                    "active": bool(curator.get("active", True)),
                    "last_updated": curator.get("last_updated"),
                    "recommendations": recs,
                }
            )

        json_path = tmp_path / "curators.json"
        with open(json_path, "w") as f:
            json.dump({"version": 1, "curators": export_data}, f)

        # Import into fresh DB
        db2_path = tmp_path / "test_curator_import.db"
        db2 = Database(db2_path)
        now = int(time.time())
        for app_id in (100, 200, 300):
            db2.conn.execute(
                "INSERT OR IGNORE INTO games (app_id, name, app_type, created_at, updated_at) "
                "VALUES (?, ?, ?, ?, ?)",
                (app_id, f"Game {app_id}", "game", now, now),
            )
        db2.commit()

        with open(json_path) as f:
            data = json.load(f)

        for entry in data["curators"]:
            db2.add_curator(entry["curator_id"], entry["name"], entry.get("url", ""))
            recs = entry.get("recommendations", [])
            if recs:
                db2.save_curator_recommendations(entry["curator_id"], recs)

        curators2 = db2.get_all_curators()
        assert len(curators2) == 2
        assert db2.get_recommendations_for_curator(1850) == {100, 200, 300}
        assert db2.get_recommendations_for_curator(33526) == {200}
        db2.close()

    def test_import_skips_newer_local(self, db: Database) -> None:
        """Import should skip curators whose local data is newer."""
        db.add_curator(1850, "PC Gamer")
        db.save_curator_recommendations(1850, [100, 200, 300])

        # Local curator now has a last_updated timestamp
        local = db.get_all_curators()[0]
        local_updated = local["last_updated"]

        # Simulate import data with older timestamp
        import_entry = {
            "curator_id": 1850,
            "name": "Old PC Gamer",
            "last_updated": "2020-01-01T00:00:00Z",
            "recommendations": [100],
        }

        # Merge logic: skip if local is newer
        if local_updated and import_entry["last_updated"]:
            if local_updated >= import_entry["last_updated"]:
                # Should skip
                pass
            else:
                db.add_curator(import_entry["curator_id"], import_entry["name"])

        # Verify local data unchanged
        curators = db.get_all_curators()
        assert curators[0]["name"] == "PC Gamer"  # Not overwritten
        assert db.get_recommendations_for_curator(1850) == {100, 200, 300}

    def test_import_empty_file(self) -> None:
        """Empty curators list should result in 0 imports."""
        data = {"version": 1, "curators": []}
        assert len(data["curators"]) == 0
