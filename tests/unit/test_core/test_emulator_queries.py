"""Tests for EmulatorQueriesMixin database operations (Schema v12)."""

from __future__ import annotations

from pathlib import Path

import pytest

from steam_library_manager.core.db import Database


@pytest.fixture
def db(tmp_path: Path) -> Database:
    return Database(tmp_path / "test.db")


class TestSchemaV12:
    def test_schema_version_is_12(self, db: Database) -> None:
        assert db._get_schema_version() == 12

    def test_emulator_tables_exist(self, db: Database) -> None:
        cur = db.conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name IN ('emulator_settings', 'emulator_games')"
        )
        names = sorted(r[0] for r in cur.fetchall())
        assert names == ["emulator_games", "emulator_settings"]


class TestEmulatorSettings:
    def test_upsert_creates_row(self, db: Database) -> None:
        db.upsert_emulator_settings("Eden", enabled=True, default_for_system="switch")
        s = db.get_emulator_settings("Eden")
        assert s is not None
        assert s["emulator_name"] == "Eden"
        assert s["enabled"] is True
        assert s["default_for_system"] == "switch"
        assert s["custom_game_dirs"] == []

    def test_upsert_updates_existing(self, db: Database) -> None:
        db.upsert_emulator_settings("Eden", enabled=True)
        db.upsert_emulator_settings("Eden", enabled=False)
        s = db.get_emulator_settings("Eden")
        assert s["enabled"] is False

    def test_get_missing_returns_none(self, db: Database) -> None:
        assert db.get_emulator_settings("DoesNotExist") is None

    def test_get_all_returns_sorted(self, db: Database) -> None:
        db.upsert_emulator_settings("Ryujinx")
        db.upsert_emulator_settings("Eden")
        db.upsert_emulator_settings("Cemu")
        names = [s["emulator_name"] for s in db.get_all_emulator_settings()]
        assert names == ["Cemu", "Eden", "Ryujinx"]

    def test_set_enabled_creates_row(self, db: Database) -> None:
        db.set_emulator_enabled("Eden", False)
        s = db.get_emulator_settings("Eden")
        assert s is not None
        assert s["enabled"] is False

    def test_set_default_clears_old_default(self, db: Database) -> None:
        db.set_default_emulator_for_system("switch", "Eden")
        db.set_default_emulator_for_system("switch", "Ryujinx")
        assert db.get_default_emulator_for_system("switch") == "Ryujinx"
        eden = db.get_emulator_settings("Eden")
        assert eden["default_for_system"] == ""

    def test_default_only_returned_for_enabled(self, db: Database) -> None:
        db.set_default_emulator_for_system("switch", "Eden")
        db.set_emulator_enabled("Eden", False)
        assert db.get_default_emulator_for_system("switch") is None

    def test_add_custom_game_dir(self, db: Database) -> None:
        db.add_custom_game_dir("Eden", "/mnt/games/Emulation/roms/switch")
        s = db.get_emulator_settings("Eden")
        assert s["custom_game_dirs"] == ["/mnt/games/Emulation/roms/switch"]

    def test_add_custom_game_dir_dedups(self, db: Database) -> None:
        db.add_custom_game_dir("Eden", "/path/a")
        db.add_custom_game_dir("Eden", "/path/a")
        assert db.get_emulator_settings("Eden")["custom_game_dirs"] == ["/path/a"]

    def test_remove_custom_game_dir(self, db: Database) -> None:
        db.add_custom_game_dir("Eden", "/path/a")
        db.add_custom_game_dir("Eden", "/path/b")
        db.remove_custom_game_dir("Eden", "/path/a")
        assert db.get_emulator_settings("Eden")["custom_game_dirs"] == ["/path/b"]

    def test_set_executable_override(self, db: Database) -> None:
        db.set_executable_override("Eden", "/opt/eden/Eden.AppImage")
        assert db.get_emulator_settings("Eden")["executable_override"] == "/opt/eden/Eden.AppImage"


class TestEmulatorGames:
    def test_upsert_emulator_game(self, db: Database) -> None:
        db.upsert_emulator_game("Eden", "switch", "/roms/Metroid.nsp", "Metroid Dread")
        games = db.get_emulator_games()
        assert len(games) == 1
        assert games[0]["game_name"] == "Metroid Dread"
        assert games[0]["emulator_name"] == "Eden"
        assert games[0]["system"] == "switch"

    def test_upsert_changes_emulator_for_same_rom(self, db: Database) -> None:
        db.upsert_emulator_game("Eden", "switch", "/roms/Metroid.nsp", "Metroid Dread")
        db.upsert_emulator_game("Ryujinx", "switch", "/roms/Metroid.nsp", "Metroid Dread")
        games = db.get_emulator_games()
        assert len(games) == 1
        assert games[0]["emulator_name"] == "Ryujinx"

    def test_bulk_upsert(self, db: Database) -> None:
        rows = [
            ("Eden", "switch", "/roms/a.nsp", "Game A"),
            ("Eden", "switch", "/roms/b.nsp", "Game B"),
            ("Cemu", "wiiu", "/roms/c.wud", "Game C"),
        ]
        db.bulk_upsert_emulator_games(rows)
        assert len(db.get_emulator_games()) == 3

    def test_bulk_upsert_empty(self, db: Database) -> None:
        db.bulk_upsert_emulator_games([])
        assert db.get_emulator_games() == []

    def test_filter_by_system(self, db: Database) -> None:
        db.upsert_emulator_game("Eden", "switch", "/r/a.nsp", "A")
        db.upsert_emulator_game("Cemu", "wiiu", "/r/b.wud", "B")
        switch_games = db.get_emulator_games(system="switch")
        assert len(switch_games) == 1
        assert switch_games[0]["game_name"] == "A"

    def test_filter_by_emulator(self, db: Database) -> None:
        db.upsert_emulator_game("Eden", "switch", "/r/a.nsp", "A")
        db.upsert_emulator_game("Cemu", "wiiu", "/r/b.wud", "B")
        eden_games = db.get_emulator_games(emulator_name="Eden")
        assert len(eden_games) == 1
        assert eden_games[0]["game_name"] == "A"

    def test_mark_added_to_steam(self, db: Database) -> None:
        db.upsert_emulator_game("Eden", "switch", "/r/a.nsp", "A")
        assert db.get_emulator_games()[0]["added_to_steam"] == 0
        db.mark_emulator_game_added_to_steam("/r/a.nsp")
        assert db.get_emulator_games()[0]["added_to_steam"] == 1

    def test_clear_all_games(self, db: Database) -> None:
        db.upsert_emulator_game("Eden", "switch", "/r/a.nsp", "A")
        db.upsert_emulator_game("Cemu", "wiiu", "/r/b.wud", "B")
        db.clear_emulator_games()
        assert db.get_emulator_games() == []

    def test_clear_per_emulator(self, db: Database) -> None:
        db.upsert_emulator_game("Eden", "switch", "/r/a.nsp", "A")
        db.upsert_emulator_game("Cemu", "wiiu", "/r/b.wud", "B")
        db.clear_emulator_games(emulator_name="Eden")
        rest = db.get_emulator_games()
        assert len(rest) == 1
        assert rest[0]["emulator_name"] == "Cemu"
