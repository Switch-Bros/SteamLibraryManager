"""Tests for Heroic Amazon Games parser."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

from src.integrations.external_games.heroic_amazon_parser import HeroicAmazonParser


class TestHeroicAmazonParser:
    """Tests for Amazon games via Heroic/Nile."""

    def _write_config(self, tmp_path: Path, data: list | dict) -> Path:
        """Write test installed.json."""
        config = tmp_path / "installed.json"
        config.write_text(json.dumps(data), encoding="utf-8")
        return config

    def test_parse_nile_format(self, tmp_path: Path) -> None:
        """Parse Amazon/Nile format (plain JSON array)."""
        data = [
            {
                "id": "amzn1.adg.product.ec0f0479-ce53-4495-b5d5-907ec268098b",
                "version": "3e71c02f-421d-4c4f-a57f-1170e7e4122e",
                "path": "/home/user/Games/Heroic/A Tiny Sticker Tale",
                "size": 761585661,
            }
        ]
        config = self._write_config(tmp_path, data)
        parser = HeroicAmazonParser()

        with patch.object(parser, "get_config_paths", return_value=[config]):
            games = parser.read_games()

        assert len(games) == 1
        assert games[0].platform == "Heroic (Amazon)"
        assert games[0].name == "A Tiny Sticker Tale"
        assert games[0].install_size == 761585661
        assert "nile" in games[0].launch_command

    def test_name_from_path(self, tmp_path: Path) -> None:
        """Name is extracted from path (last component)."""
        data = [{"id": "amzn1.test", "path": "/Games/My Cool Game", "size": 0}]
        config = self._write_config(tmp_path, data)
        parser = HeroicAmazonParser()

        with patch.object(parser, "get_config_paths", return_value=[config]):
            games = parser.read_games()

        assert games[0].name == "My Cool Game"

    def test_empty_array(self, tmp_path: Path) -> None:
        """Empty array returns empty list."""
        config = self._write_config(tmp_path, [])
        parser = HeroicAmazonParser()

        with patch.object(parser, "get_config_paths", return_value=[config]):
            assert parser.read_games() == []

    def test_not_installed(self) -> None:
        """Returns empty list when no config exists."""
        parser = HeroicAmazonParser()
        with patch.object(parser, "get_config_paths", return_value=[Path("/nonexistent")]):
            assert parser.read_games() == []

    def test_dict_format_rejected(self, tmp_path: Path) -> None:
        """Dict format (wrong type) returns empty list."""
        config = self._write_config(tmp_path, {"key": "value"})
        parser = HeroicAmazonParser()

        with patch.object(parser, "get_config_paths", return_value=[config]):
            assert parser.read_games() == []

    def test_string_size_handled(self, tmp_path: Path) -> None:
        """String size values are handled gracefully."""
        data = [{"id": "test", "path": "/Games/Test", "size": "unknown"}]
        config = self._write_config(tmp_path, data)
        parser = HeroicAmazonParser()

        with patch.object(parser, "get_config_paths", return_value=[config]):
            games = parser.read_games()

        assert games[0].install_size == 0
