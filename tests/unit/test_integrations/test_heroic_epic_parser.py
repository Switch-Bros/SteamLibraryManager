"""Tests for Heroic Epic Games parser."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

from src.integrations.external_games.heroic_epic_parser import HeroicEpicParser


class TestHeroicEpicParser:
    """Tests for Epic Games via Heroic/Legendary."""

    def _write_config(self, tmp_path: Path, data: dict | list) -> Path:
        """Write test installed.json and patch config paths."""
        config = tmp_path / "installed.json"
        config.write_text(json.dumps(data), encoding="utf-8")
        return config

    def test_parse_installed_json(self, tmp_path: Path) -> None:
        """Parse a standard Epic installed.json dict."""
        data = {
            "4656facc740742a39e265b026e13d075": {
                "app_name": "4656facc740742a39e265b026e13d075",
                "title": "20 Minutes Till Dawn",
                "executable": "MinutesTillDawn.exe",
                "install_path": "/home/user/Games/Heroic/MinutesTillDawn",
                "install_size": 133450712,
                "platform": "Windows",
                "can_run_offline": True,
                "is_dlc": False,
            }
        }
        config = self._write_config(tmp_path, data)
        parser = HeroicEpicParser()

        with patch.object(parser, "get_config_paths", return_value=[config]):
            games = parser.read_games()

        assert len(games) == 1
        assert games[0].name == "20 Minutes Till Dawn"
        assert games[0].platform == "Heroic (Epic)"
        assert games[0].install_size == 133450712
        assert "heroic://launch/" in games[0].launch_command

    def test_skip_dlc(self, tmp_path: Path) -> None:
        """DLC entries are filtered out."""
        data = {
            "game1": {"title": "Base Game", "is_dlc": False},
            "dlc1": {"title": "DLC Pack", "is_dlc": True},
        }
        config = self._write_config(tmp_path, data)
        parser = HeroicEpicParser()

        with patch.object(parser, "get_config_paths", return_value=[config]):
            games = parser.read_games()

        assert len(games) == 1
        assert games[0].name == "Base Game"

    def test_not_installed(self) -> None:
        """Returns empty list when no config file exists."""
        parser = HeroicEpicParser()
        with patch.object(parser, "get_config_paths", return_value=[Path("/nonexistent")]):
            assert parser.read_games() == []
            assert parser.is_available() is False

    def test_empty_json(self, tmp_path: Path) -> None:
        """Empty installed.json returns empty list."""
        config = self._write_config(tmp_path, {})
        parser = HeroicEpicParser()

        with patch.object(parser, "get_config_paths", return_value=[config]):
            assert parser.read_games() == []

    def test_multiple_games(self, tmp_path: Path) -> None:
        """Multiple games are all parsed."""
        data = {
            "g1": {"title": "Game 1", "install_size": 100},
            "g2": {"title": "Game 2", "install_size": 200},
            "g3": {"title": "Game 3", "install_size": 300},
        }
        config = self._write_config(tmp_path, data)
        parser = HeroicEpicParser()

        with patch.object(parser, "get_config_paths", return_value=[config]):
            games = parser.read_games()

        assert len(games) == 3

    def test_flatpak_launch_command(self, tmp_path: Path) -> None:
        """Flatpak Heroic uses flatpak run command."""
        flatpak_dir = tmp_path / ".var" / "app" / "com.heroicgameslauncher.hgl"
        flatpak_dir.mkdir(parents=True)
        config = flatpak_dir / "installed.json"
        config.write_text(json.dumps({"g1": {"title": "Game"}}))

        parser = HeroicEpicParser()
        with (
            patch.object(parser, "get_config_paths", return_value=[config]),
            patch("src.integrations.external_games.heroic_epic_parser.Path") as mock_path,
        ):
            mock_path.home.return_value = tmp_path
            games = parser.read_games()

        assert len(games) == 1
        assert "flatpak run" in games[0].launch_command
