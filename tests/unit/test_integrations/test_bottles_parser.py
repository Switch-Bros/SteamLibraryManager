"""Tests for Bottles parser."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

yaml = pytest.importorskip("yaml")

from src.integrations.external_games.bottles_parser import BottlesParser  # noqa: E402


class TestBottlesParser:
    """Tests for Bottles YAML parsing."""

    def _create_bottle(self, base: Path, bottle_name: str, programs: dict) -> None:
        """Create a test bottle.yml."""
        bottle_dir = base / "bottles" / bottle_name
        bottle_dir.mkdir(parents=True)
        data = {"Name": bottle_name, "External_Programs": programs}
        (bottle_dir / "bottle.yml").write_text(yaml.dump(data), encoding="utf-8")

    def test_parse_bottle_yml(self, tmp_path: Path) -> None:
        """Parse External_Programs from bottle.yml."""
        self._create_bottle(
            tmp_path,
            "Gaming",
            {
                "uuid-1": {
                    "name": "Notepad++",
                    "executable": "notepad++.exe",
                    "path": "C:\\Program Files\\Notepad++",
                    "id": "uuid-1",
                }
            },
        )

        parser = BottlesParser()
        with patch.object(parser, "_get_base_paths", return_value=[tmp_path]):
            games = parser.read_games()

        assert len(games) == 1
        assert games[0].name == "Notepad++"
        assert games[0].platform == "Bottles"
        assert "Gaming" in games[0].launch_command

    def test_empty_external_programs(self, tmp_path: Path) -> None:
        """Empty External_Programs returns empty list."""
        self._create_bottle(tmp_path, "Empty", {})

        parser = BottlesParser()
        with patch.object(parser, "_get_base_paths", return_value=[tmp_path]):
            assert parser.read_games() == []

    def test_no_bottles_dir(self, tmp_path: Path) -> None:
        """Returns empty list when no bottles directory exists."""
        parser = BottlesParser()
        with patch.object(parser, "_get_base_paths", return_value=[tmp_path / "nonexistent"]):
            assert parser.read_games() == []

    def test_multiple_bottles(self, tmp_path: Path) -> None:
        """Programs from multiple bottles are collected."""
        self._create_bottle(
            tmp_path,
            "Games",
            {
                "u1": {"name": "Game A", "id": "u1"},
            },
        )
        self._create_bottle(
            tmp_path,
            "Tools",
            {
                "u2": {"name": "Tool B", "id": "u2"},
            },
        )

        parser = BottlesParser()
        with patch.object(parser, "_get_base_paths", return_value=[tmp_path]):
            games = parser.read_games()

        assert len(games) == 2
        names = {g.name for g in games}
        assert names == {"Game A", "Tool B"}

    def test_library_yml_entries(self, tmp_path: Path) -> None:
        """library.yml entries are also detected."""
        (tmp_path / "bottles").mkdir(parents=True)
        library = {
            "uuid-lib": {
                "name": "Library Game",
                "bottle": {"name": "Gaming"},
            }
        }
        (tmp_path / "library.yml").write_text(yaml.dump(library))

        parser = BottlesParser()
        with patch.object(parser, "_get_base_paths", return_value=[tmp_path]):
            games = parser.read_games()

        assert len(games) == 1
        assert games[0].name == "Library Game"

    def test_dedup_across_sources(self, tmp_path: Path) -> None:
        """Duplicate names across bottle.yml and library.yml are deduped."""
        self._create_bottle(
            tmp_path,
            "Gaming",
            {
                "u1": {"name": "SharedGame", "id": "u1"},
            },
        )
        library = {"u2": {"name": "SharedGame", "bottle": {"name": "Gaming"}}}
        (tmp_path / "library.yml").write_text(yaml.dump(library))

        parser = BottlesParser()
        with patch.object(parser, "_get_base_paths", return_value=[tmp_path]):
            games = parser.read_games()

        assert len(games) == 1
