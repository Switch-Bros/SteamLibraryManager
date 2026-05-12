"""Tests for Heroic sideload parser."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

from steam_library_manager.integrations.external_games.heroic_sideload_parser import (
    HeroicSideloadParser,
)


class TestHeroicSideloadParser:
    """Tests for Heroic Sideload (manually added) games."""

    def _write_config(self, tmp_path: Path, data: dict) -> Path:
        """Write test library.json into a fake heroic config structure."""
        config_dir = tmp_path / "sideload_apps"
        config_dir.mkdir(parents=True)
        config = config_dir / "library.json"
        config.write_text(json.dumps(data), encoding="utf-8")
        return config

    def test_platform_name(self) -> None:
        """Parser identifies itself as 'Heroic (Sideload)'."""
        parser = HeroicSideloadParser()
        assert parser.platform_name() == "Heroic (Sideload)"

    def test_is_available_when_config_exists(self, tmp_path: Path) -> None:
        """is_available returns True when library.json exists."""
        config = self._write_config(tmp_path, {"games": []})
        parser = HeroicSideloadParser()
        with patch.object(parser, "get_config_paths", return_value=[config]):
            assert parser.is_available() is True

    def test_is_available_when_no_config(self) -> None:
        """is_available returns False when no library.json found."""
        parser = HeroicSideloadParser()
        with patch.object(parser, "get_config_paths", return_value=[Path("/nonexistent")]):
            assert parser.is_available() is False

    def test_reads_installed_sideload_games(self, tmp_path: Path) -> None:
        """Parse games array with installed sideload apps."""
        data = {
            "games": [
                {
                    "runner": "sideload",
                    "app_name": "mM3s2otsF81v7v91MddJe3",
                    "title": "WarCraft 2 remastered",
                    "install": {
                        "executable": "/mnt/games/Warcraft/WC2/Warcraft II.exe",
                        "platform": "Windows",
                        "is_dlc": False,
                    },
                    "folder_name": "/mnt/games/Warcraft/WC2",
                    "art_cover": "https://cdn2.steamgriddb.com/grid/abc.png",
                    "is_installed": True,
                    "art_square": "https://cdn2.steamgriddb.com/grid/abc.png",
                    "canRunOffline": True,
                    "browserUrl": "",
                    "customUserAgent": "",
                    "launchFullScreen": False,
                },
                {
                    "runner": "sideload",
                    "app_name": "9pitf5MdpcuBBLqiMK4kqR",
                    "title": "Adobe Photoshop 2024",
                    "install": {
                        "executable": "/home/u/Prefixes/PS/Photoshop.exe",
                        "platform": "Windows",
                        "is_dlc": False,
                    },
                    "folder_name": "/home/u/Prefixes/PS",
                    "art_cover": "https://cdn2.steamgriddb.com/grid/def.png",
                    "is_installed": True,
                },
            ]
        }
        config = self._write_config(tmp_path, data)
        parser = HeroicSideloadParser()

        with patch.object(parser, "get_config_paths", return_value=[config]):
            games = parser.read_games()

        assert len(games) == 2
        warcraft = next(g for g in games if g.platform_app_id == "mM3s2otsF81v7v91MddJe3")
        assert warcraft.platform == "Heroic (Sideload)"
        assert warcraft.name == "WarCraft 2 remastered"
        assert warcraft.executable == "/mnt/games/Warcraft/WC2/Warcraft II.exe"
        assert warcraft.install_path == Path("/mnt/games/Warcraft/WC2")

    def test_launch_command_uses_heroic_uri(self, tmp_path: Path) -> None:
        """Launch command is heroic://launch URI with sideload runner."""
        data = {
            "games": [
                {
                    "runner": "sideload",
                    "app_name": "ABC123",
                    "title": "Test",
                    "install": {"executable": "/p/test.exe"},
                    "folder_name": "/p",
                    "is_installed": True,
                }
            ]
        }
        config = self._write_config(tmp_path, data)
        parser = HeroicSideloadParser()

        with patch.object(parser, "get_config_paths", return_value=[config]):
            games = parser.read_games()

        assert games[0].launch_command == "heroic://launch/ABC123?runner=sideload"

    def test_flatpak_launch_command(self, tmp_path: Path) -> None:
        """Flatpak Heroic install wraps launch command in flatpak run."""
        flatpak_root = tmp_path / ".var" / "app" / "com.heroicgameslauncher.hgl" / "config" / "heroic"
        sideload_dir = flatpak_root / "sideload_apps"
        sideload_dir.mkdir(parents=True)
        config = sideload_dir / "library.json"
        config.write_text(
            json.dumps(
                {
                    "games": [
                        {
                            "runner": "sideload",
                            "app_name": "ABC123",
                            "title": "Test",
                            "install": {"executable": "/p/test.exe"},
                            "folder_name": "/p",
                            "is_installed": True,
                        }
                    ]
                }
            ),
            encoding="utf-8",
        )
        parser = HeroicSideloadParser()

        with patch.object(parser, "get_config_paths", return_value=[config]):
            games = parser.read_games()

        expected = (
            'flatpak run com.heroicgameslauncher.hgl --no-gui --no-sandbox "heroic://launch/ABC123?runner=sideload"'
        )
        assert games[0].launch_command == expected

    def test_name_fallback_to_app_name_when_title_missing(self, tmp_path: Path) -> None:
        """If title is missing or empty, fall back to app_name."""
        data = {
            "games": [
                {
                    "runner": "sideload",
                    "app_name": "OnlyAppName",
                    "install": {"executable": "/p/test.exe"},
                    "folder_name": "/p",
                    "is_installed": True,
                }
            ]
        }
        config = self._write_config(tmp_path, data)
        parser = HeroicSideloadParser()

        with patch.object(parser, "get_config_paths", return_value=[config]):
            games = parser.read_games()

        assert games[0].name == "OnlyAppName"
