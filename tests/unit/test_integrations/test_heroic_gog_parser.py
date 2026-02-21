"""Tests for Heroic GOG parser."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

from src.integrations.external_games.heroic_gog_parser import (
    HeroicGOGParser,
    _parse_size_string,
)


class TestParseSizeString:
    """Tests for human-readable size string parsing."""

    def test_mib(self) -> None:
        """Parse MiB size string."""
        assert _parse_size_string("27.8 MiB") == int(27.8 * 1024**2)

    def test_gib(self) -> None:
        """Parse GiB size string."""
        assert _parse_size_string("1.5 GiB") == int(1.5 * 1024**3)

    def test_bytes(self) -> None:
        """Parse plain bytes."""
        assert _parse_size_string("1024 B") == 1024

    def test_invalid_returns_zero(self) -> None:
        """Invalid string returns 0."""
        assert _parse_size_string("unknown") == 0
        assert _parse_size_string("") == 0

    def test_mb_decimal(self) -> None:
        """Parse MB (decimal, not binary)."""
        assert _parse_size_string("100 MB") == 100 * 1000**2


class TestHeroicGOGParser:
    """Tests for GOG games via Heroic."""

    def _write_config(self, tmp_path: Path, data: dict) -> Path:
        """Write test installed.json."""
        config_dir = tmp_path / "gog_store"
        config_dir.mkdir(parents=True)
        config = config_dir / "installed.json"
        config.write_text(json.dumps(data), encoding="utf-8")
        return config

    def test_parse_installed_array(self, tmp_path: Path) -> None:
        """Parse GOG format with 'installed' array."""
        data = {
            "installed": [
                {
                    "platform": "windows",
                    "install_path": "/home/user/Games/Heroic/Eye of the Beholder",
                    "install_size": "27.8 MiB",
                    "is_dlc": False,
                    "version": "1.7",
                    "appName": "1432575012",
                    "language": "de-DE",
                }
            ]
        }
        config = self._write_config(tmp_path, data)
        parser = HeroicGOGParser()

        with patch.object(parser, "get_config_paths", return_value=[config]):
            games = parser.read_games()

        assert len(games) == 1
        assert games[0].platform == "Heroic (GOG)"
        assert games[0].platform_app_id == "1432575012"
        assert games[0].install_size == int(27.8 * 1024**2)
        meta = dict(games[0].platform_metadata)
        assert meta["version"] == "1.7"
        assert meta["language"] == "de-DE"

    def test_name_from_path(self, tmp_path: Path) -> None:
        """Name is extracted from install_path when no metadata available."""
        data = {
            "installed": [
                {
                    "appName": "999",
                    "install_path": "/Games/Eye of the Beholder",
                    "install_size": "1 MiB",
                }
            ]
        }
        config = self._write_config(tmp_path, data)
        parser = HeroicGOGParser()

        with patch.object(parser, "get_config_paths", return_value=[config]):
            games = parser.read_games()

        assert games[0].name == "Eye of the Beholder"

    def test_name_from_store_cache(self, tmp_path: Path) -> None:
        """Name is resolved from store_cache metadata."""
        data = {"installed": [{"appName": "123", "install_path": "/path/to/game"}]}
        config = self._write_config(tmp_path, data)
        # Create store_cache metadata
        cache_dir = tmp_path / "store_cache"
        cache_dir.mkdir()
        (cache_dir / "123.json").write_text(json.dumps({"title": "Real Title"}))

        parser = HeroicGOGParser()

        with patch.object(parser, "get_config_paths", return_value=[config]):
            games = parser.read_games()

        assert games[0].name == "Real Title"

    def test_skip_dlc(self, tmp_path: Path) -> None:
        """DLC entries are filtered out."""
        data = {
            "installed": [
                {"appName": "g1", "install_path": "/p/Game", "is_dlc": False},
                {"appName": "d1", "install_path": "/p/DLC", "is_dlc": True},
            ]
        }
        config = self._write_config(tmp_path, data)
        parser = HeroicGOGParser()

        with patch.object(parser, "get_config_paths", return_value=[config]):
            games = parser.read_games()

        assert len(games) == 1

    def test_not_installed(self) -> None:
        """Returns empty list when no config exists."""
        parser = HeroicGOGParser()
        with patch.object(parser, "get_config_paths", return_value=[Path("/nonexistent")]):
            assert parser.read_games() == []

    def test_empty_installed_array(self, tmp_path: Path) -> None:
        """Empty installed array returns empty list."""
        config = self._write_config(tmp_path, {"installed": []})
        parser = HeroicGOGParser()

        with patch.object(parser, "get_config_paths", return_value=[config]):
            assert parser.read_games() == []
