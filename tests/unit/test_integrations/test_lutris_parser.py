"""Tests for Lutris parser."""

from __future__ import annotations

import sqlite3
from pathlib import Path
from unittest.mock import patch

from src.integrations.external_games.lutris_parser import LutrisParser


class TestLutrisParser:
    """Tests for Lutris pga.db parsing."""

    def _create_db(self, tmp_path: Path) -> Path:
        """Create a test Lutris pga.db with schema."""
        db_path = tmp_path / "pga.db"
        conn = sqlite3.connect(str(db_path))
        conn.execute("""
            CREATE TABLE games (
                id INTEGER PRIMARY KEY,
                name TEXT, slug TEXT, runner TEXT,
                executable TEXT, directory TEXT,
                installed INTEGER DEFAULT 0,
                service TEXT, service_id TEXT,
                year INTEGER, platform TEXT
            )
        """)
        conn.commit()
        conn.close()
        return db_path

    def _insert_game(self, db_path: Path, **kwargs: object) -> None:
        """Insert a game row into the test database."""
        defaults = {
            "name": "Test",
            "slug": "test",
            "runner": "wine",
            "executable": "",
            "directory": "",
            "installed": 1,
            "service": "",
            "service_id": "",
            "year": 0,
            "platform": "",
        }
        defaults.update(kwargs)
        conn = sqlite3.connect(str(db_path))
        conn.execute(
            "INSERT INTO games (name, slug, runner, executable, directory, "
            "installed, service, service_id, year, platform) "
            "VALUES (:name, :slug, :runner, :executable, :directory, "
            ":installed, :service, :service_id, :year, :platform)",
            defaults,
        )
        conn.commit()
        conn.close()

    def test_parse_pga_db(self, tmp_path: Path) -> None:
        """Parse games from a Lutris database."""
        db_path = self._create_db(tmp_path)
        self._insert_game(
            db_path, name="Alice: Madness Returns", slug="alice", runner="wine", service="ea_app", installed=1
        )

        parser = LutrisParser()
        with patch.object(parser, "get_config_paths", return_value=[db_path]):
            games = parser.read_games()

        assert len(games) == 1
        assert games[0].name == "Alice: Madness Returns"
        assert games[0].platform == "Lutris"
        assert "lutris:rungame/alice" in games[0].launch_command

    def test_filter_launchers(self, tmp_path: Path) -> None:
        """Known launcher names are filtered out."""
        db_path = self._create_db(tmp_path)
        self._insert_game(db_path, name="Real Game", slug="game", runner="wine", service="ea_app")
        self._insert_game(db_path, name="Epic Games Store", slug="epic", runner="wine")
        self._insert_game(db_path, name="EA App", slug="ea", runner="wine")
        self._insert_game(db_path, name="Ubisoft Connect", slug="ubi", runner="wine")

        parser = LutrisParser()
        with patch.object(parser, "get_config_paths", return_value=[db_path]):
            games = parser.read_games()

        assert len(games) == 1
        assert games[0].name == "Real Game"

    def test_db_not_found(self) -> None:
        """Returns empty list when database doesn't exist."""
        parser = LutrisParser()
        with patch.object(parser, "get_config_paths", return_value=[Path("/nonexistent")]):
            assert parser.read_games() == []

    def test_uninstalled_skipped(self, tmp_path: Path) -> None:
        """Games with installed=0 are not returned."""
        db_path = self._create_db(tmp_path)
        self._insert_game(db_path, name="Installed", slug="inst", runner="wine", installed=1)
        self._insert_game(db_path, name="Removed", slug="rem", runner="wine", installed=0)

        parser = LutrisParser()
        with patch.object(parser, "get_config_paths", return_value=[db_path]):
            games = parser.read_games()

        assert len(games) == 1
        assert games[0].name == "Installed"

    def test_no_runner_skipped(self, tmp_path: Path) -> None:
        """Games without a runner are not returned."""
        db_path = self._create_db(tmp_path)
        self._insert_game(db_path, name="NoRunner", slug="nr", runner="", installed=1)

        parser = LutrisParser()
        with patch.object(parser, "get_config_paths", return_value=[db_path]):
            assert parser.read_games() == []
