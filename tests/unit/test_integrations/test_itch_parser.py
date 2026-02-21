"""Tests for itch.io parser."""

from __future__ import annotations

import sqlite3
from pathlib import Path
from unittest.mock import patch

from src.integrations.external_games.itch_parser import ItchParser


class TestItchParser:
    """Tests for itch.io butler.db parsing."""

    def _create_db(self, tmp_path: Path) -> Path:
        """Create a test butler.db with schema."""
        db_path = tmp_path / "butler.db"
        conn = sqlite3.connect(str(db_path))
        conn.executescript("""
            CREATE TABLE games (
                id INTEGER PRIMARY KEY,
                title TEXT, short_text TEXT, cover_url TEXT,
                classification TEXT, url TEXT
            );
            CREATE TABLE install_locations (
                id TEXT PRIMARY KEY,
                path TEXT
            );
            CREATE TABLE caves (
                id TEXT PRIMARY KEY,
                game_id INTEGER,
                installed_size INTEGER,
                seconds_run INTEGER,
                installed_at TEXT,
                install_folder_name TEXT,
                custom_install_folder TEXT,
                install_location_id TEXT
            );
        """)
        conn.commit()
        conn.close()
        return db_path

    def _insert_game(
        self,
        db_path: Path,
        game_id: int,
        title: str,
        cave_id: str = "cave1",
        classification: str = "game",
        folder: str = "game_folder",
        location_id: str = "loc1",
    ) -> None:
        """Insert a game with cave and location data."""
        conn = sqlite3.connect(str(db_path))
        conn.execute(
            "INSERT OR IGNORE INTO games (id, title, classification, url) VALUES (?, ?, ?, ?)",
            (game_id, title, classification, f"https://itch.io/{title}"),
        )
        conn.execute(
            "INSERT OR IGNORE INTO install_locations (id, path) VALUES (?, ?)",
            (location_id, "/home/user/.config/itch/apps"),
        )
        conn.execute(
            "INSERT INTO caves (id, game_id, installed_size, seconds_run, "
            "install_folder_name, install_location_id) VALUES (?, ?, ?, ?, ?, ?)",
            (cave_id, game_id, 50000, 120, folder, location_id),
        )
        conn.commit()
        conn.close()

    def test_parse_butler_db(self, tmp_path: Path) -> None:
        """Parse games from butler.db."""
        db_path = self._create_db(tmp_path)
        self._insert_game(db_path, 1, "Cool Game", "c1")

        parser = ItchParser()
        with patch("src.integrations.external_games.itch_parser._get_db_path", return_value=db_path):
            games = parser.read_games()

        assert len(games) == 1
        assert games[0].name == "Cool Game"
        assert games[0].platform == "itch.io"
        assert "itch://caves/c1/launch" in games[0].launch_command

    def test_filter_non_games(self, tmp_path: Path) -> None:
        """Non-game classifications are filtered."""
        db_path = self._create_db(tmp_path)
        self._insert_game(db_path, 1, "A Game", "c1", classification="game")
        self._insert_game(db_path, 2, "A Book", "c2", classification="book")
        self._insert_game(db_path, 3, "A Comic", "c3", classification="comic")
        self._insert_game(db_path, 4, "A Tool", "c4", classification="tool")

        parser = ItchParser()
        with patch("src.integrations.external_games.itch_parser._get_db_path", return_value=db_path):
            games = parser.read_games()

        assert len(games) == 2
        names = {g.name for g in games}
        assert names == {"A Game", "A Tool"}

    def test_db_not_found(self, tmp_path: Path) -> None:
        """Returns empty list when butler.db doesn't exist."""
        parser = ItchParser()
        with patch(
            "src.integrations.external_games.itch_parser._get_db_path",
            return_value=tmp_path / "nonexistent.db",
        ):
            assert parser.read_games() == []

    def test_custom_install_folder(self, tmp_path: Path) -> None:
        """Custom install folder takes precedence over location_path."""
        db_path = self._create_db(tmp_path)
        conn = sqlite3.connect(str(db_path))
        conn.execute("INSERT INTO games (id, title, classification) VALUES (1, 'Game', 'game')")
        conn.execute(
            "INSERT INTO caves (id, game_id, installed_size, install_folder_name, "
            "custom_install_folder) VALUES ('c1', 1, 100, 'default', '/custom/path')"
        )
        conn.commit()
        conn.close()

        parser = ItchParser()
        with patch("src.integrations.external_games.itch_parser._get_db_path", return_value=db_path):
            games = parser.read_games()

        assert games[0].install_path == Path("/custom/path")
