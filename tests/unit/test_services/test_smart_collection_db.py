# tests/unit/test_services/test_smart_collection_db.py

"""Tests for Database smart collection CRUD operations."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest

from src.core.database import Database


@pytest.fixture
def db(tmp_path: Path) -> Database:
    """Creates a Database instance with test games for FK constraints."""
    db_path = tmp_path / "test.db"
    database = Database(db_path)
    # Insert dummy games so FK constraint on collection_games.app_id is satisfied
    import time

    now = int(time.time())
    for app_id in (100, 200, 300, 400, 500):
        database.conn.execute(
            "INSERT OR IGNORE INTO games (app_id, name, app_type, created_at, updated_at) " "VALUES (?, ?, ?, ?, ?)",
            (app_id, f"Game {app_id}", "game", now, now),
        )
    database.commit()
    return database


class TestSmartCollectionCRUD:
    """Tests for smart collection create/read/update/delete."""

    def test_create_smart_collection(self, db: Database) -> None:
        """Tests creating a smart collection returns valid ID."""
        rules = json.dumps({"logic": "OR", "rules": []})
        cid = db.create_smart_collection("Test", "A test collection", "\U0001f9e0", rules)
        assert cid > 0

    def test_get_smart_collection(self, db: Database) -> None:
        """Tests retrieving a created smart collection."""
        rules = json.dumps({"logic": "AND", "rules": [{"field": "tag", "operator": "contains", "value": "LEGO"}]})
        cid = db.create_smart_collection("LEGO Games", "All LEGO", "\U0001f9e0", rules)
        db.commit()

        row = db.get_smart_collection(cid)
        assert row is not None
        assert row["name"] == "LEGO Games"
        assert row["description"] == "All LEGO"
        assert row["is_smart"] == 1
        assert "tag" in row["rules"]

    def test_get_smart_collection_not_found(self, db: Database) -> None:
        """Tests retrieving non-existent collection returns None."""
        assert db.get_smart_collection(9999) is None

    def test_update_smart_collection(self, db: Database) -> None:
        """Tests updating a smart collection's fields."""
        rules1 = json.dumps({"logic": "OR", "rules": []})
        cid = db.create_smart_collection("Original", "desc", "\U0001f9e0", rules1)
        db.commit()

        rules2 = json.dumps({"logic": "AND", "rules": [{"field": "name", "operator": "contains", "value": "test"}]})
        db.update_smart_collection(cid, "Updated", "new desc", "\U0001f3af", rules2)
        db.commit()

        row = db.get_smart_collection(cid)
        assert row is not None
        assert row["name"] == "Updated"
        assert row["description"] == "new desc"
        assert row["icon"] == "\U0001f3af"
        assert "AND" in row["rules"]

    def test_delete_smart_collection(self, db: Database) -> None:
        """Tests deleting a smart collection."""
        rules = json.dumps({"logic": "OR", "rules": []})
        cid = db.create_smart_collection("ToDelete", "", "", rules)
        db.commit()

        db.delete_smart_collection(cid)
        db.commit()

        assert db.get_smart_collection(cid) is None

    def test_delete_cascades_to_collection_games(self, db: Database) -> None:
        """Tests that deleting a collection also removes its game entries."""
        rules = json.dumps({"logic": "OR", "rules": []})
        cid = db.create_smart_collection("Cascade", "", "", rules)
        db.populate_smart_collection(cid, [100, 200, 300])
        db.commit()

        assert len(db.get_smart_collection_games(cid)) == 3

        db.delete_smart_collection(cid)
        db.commit()

        assert db.get_smart_collection_games(cid) == []

    def test_get_all_smart_collections(self, db: Database) -> None:
        """Tests retrieving all smart collections."""
        rules = json.dumps({"logic": "OR", "rules": []})
        db.create_smart_collection("Alpha", "", "", rules)
        db.create_smart_collection("Beta", "", "", rules)
        db.commit()

        all_sc = db.get_all_smart_collections()
        assert len(all_sc) == 2
        # Should be ordered by name
        assert all_sc[0]["name"] == "Alpha"
        assert all_sc[1]["name"] == "Beta"

    def test_get_all_smart_collections_only_smart(self, db: Database) -> None:
        """Tests that get_all only returns is_smart=1 collections."""
        rules = json.dumps({"logic": "OR", "rules": []})
        db.create_smart_collection("Smart", "", "", rules)
        # Manually insert a non-smart collection
        db.conn.execute(
            "INSERT INTO user_collections (name, is_smart, created_at) VALUES (?, 0, 0)",
            ("Manual",),
        )
        db.commit()

        all_sc = db.get_all_smart_collections()
        assert len(all_sc) == 1
        assert all_sc[0]["name"] == "Smart"

    def test_get_smart_collection_by_name(self, db: Database) -> None:
        """Tests retrieving a smart collection by name."""
        rules = json.dumps({"logic": "OR", "rules": []})
        db.create_smart_collection("FindMe", "found", "", rules)
        db.commit()

        row = db.get_smart_collection_by_name("FindMe")
        assert row is not None
        assert row["description"] == "found"

    def test_get_smart_collection_by_name_not_found(self, db: Database) -> None:
        """Tests that searching for non-existent name returns None."""
        assert db.get_smart_collection_by_name("DoesNotExist") is None

    def test_unique_name_constraint(self, db: Database) -> None:
        """Tests that duplicate names raise an error."""
        rules = json.dumps({"logic": "OR", "rules": []})
        db.create_smart_collection("Unique", "", "", rules)
        db.commit()

        with pytest.raises(sqlite3.IntegrityError):
            db.create_smart_collection("Unique", "", "", rules)


class TestSmartCollectionGames:
    """Tests for smart collection game membership operations."""

    def test_populate_smart_collection(self, db: Database) -> None:
        """Tests populating a collection with game IDs."""
        rules = json.dumps({"logic": "OR", "rules": []})
        cid = db.create_smart_collection("Test", "", "", rules)

        count = db.populate_smart_collection(cid, [100, 200, 300])
        db.commit()

        assert count == 3

    def test_populate_replaces_existing(self, db: Database) -> None:
        """Tests that populate replaces existing game entries."""
        rules = json.dumps({"logic": "OR", "rules": []})
        cid = db.create_smart_collection("Test", "", "", rules)

        db.populate_smart_collection(cid, [100, 200])
        db.commit()
        assert len(db.get_smart_collection_games(cid)) == 2

        db.populate_smart_collection(cid, [300, 400, 500])
        db.commit()
        games = db.get_smart_collection_games(cid)
        assert len(games) == 3
        assert set(games) == {300, 400, 500}

    def test_populate_empty_list(self, db: Database) -> None:
        """Tests populating with empty list clears games."""
        rules = json.dumps({"logic": "OR", "rules": []})
        cid = db.create_smart_collection("Test", "", "", rules)

        db.populate_smart_collection(cid, [100, 200])
        db.commit()

        count = db.populate_smart_collection(cid, [])
        db.commit()

        assert count == 0
        assert db.get_smart_collection_games(cid) == []

    def test_get_smart_collection_games(self, db: Database) -> None:
        """Tests retrieving game IDs from a collection."""
        rules = json.dumps({"logic": "OR", "rules": []})
        cid = db.create_smart_collection("Test", "", "", rules)
        db.populate_smart_collection(cid, [100, 200, 300])
        db.commit()

        games = db.get_smart_collection_games(cid)
        assert set(games) == {100, 200, 300}

    def test_get_games_empty_collection(self, db: Database) -> None:
        """Tests retrieving games from empty collection."""
        rules = json.dumps({"logic": "OR", "rules": []})
        cid = db.create_smart_collection("Empty", "", "", rules)
        db.commit()

        assert db.get_smart_collection_games(cid) == []
