"""Tests for the slim RomParser facade (delegates to EmulatorService)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

from steam_library_manager.integrations.external_games.models import ExternalGame
from steam_library_manager.integrations.external_games.rom_parser import RomParser
from steam_library_manager.services.emulator_service import GameForExport


class TestRomParserNoService:
    def test_is_unavailable_without_service(self) -> None:
        parser = RomParser()
        assert parser.is_available() is False

    def test_returns_empty_games_without_service(self) -> None:
        parser = RomParser()
        assert parser.read_games() == []

    def test_get_config_paths_empty_without_service(self) -> None:
        parser = RomParser()
        assert parser.get_config_paths() == []

    def test_platform_name(self) -> None:
        parser = RomParser()
        assert parser.platform_name() == "Emulation (ROMs)"


class TestRomParserWithService:
    def test_is_available_when_service_finds_emulators(self) -> None:
        svc = MagicMock()
        svc.detect_installed_emulators.return_value = [MagicMock()]
        parser = RomParser(emulator_service=svc)
        assert parser.is_available() is True

    def test_is_unavailable_when_no_emulators(self) -> None:
        svc = MagicMock()
        svc.detect_installed_emulators.return_value = []
        parser = RomParser(emulator_service=svc)
        assert parser.is_available() is False

    def test_read_games_calls_service_in_order(self) -> None:
        svc = MagicMock()
        svc.get_games_for_steam_export.return_value = [
            GameForExport(
                name="Metroid Dread",
                rom_path="/mnt/games/Emulation/roms/switch/Metroid Dread.nsp",
                system="switch",
                emulator_name="Eden",
                launch_command='flatpak run dev.eden_emu.eden "/mnt/games/Emulation/roms/switch/Metroid Dread.nsp"',
                system_display="Nintendo Switch",
            )
        ]
        parser = RomParser(emulator_service=svc)
        games = parser.read_games()
        svc.discover_libraries.assert_called_once()
        svc.get_games_for_steam_export.assert_called_once()
        assert len(games) == 1
        g = games[0]
        assert isinstance(g, ExternalGame)
        assert g.name == "Metroid Dread"
        assert g.platform == "Emulation (Nintendo Switch)"
        assert "Eden" in (g.executable or "")
        assert "Metroid Dread.nsp" in g.launch_command

    def test_get_config_paths_returns_existing_dirs(self, tmp_path: Path) -> None:
        rom_dir = tmp_path / "roms" / "switch"
        rom_dir.mkdir(parents=True)
        ie = MagicMock()
        ie.game_dirs = (rom_dir, Path("/nonexistent"))
        svc = MagicMock()
        svc.detect_installed_emulators.return_value = [ie]
        parser = RomParser(emulator_service=svc)
        paths = parser.get_config_paths()
        assert rom_dir in paths
        assert Path("/nonexistent") not in paths

    def test_service_exception_is_swallowed(self) -> None:
        svc = MagicMock()
        svc.detect_installed_emulators.side_effect = RuntimeError("boom")
        parser = RomParser(emulator_service=svc)
        assert parser.is_available() is False
        svc2 = MagicMock()
        svc2.discover_libraries.side_effect = RuntimeError("boom")
        parser2 = RomParser(emulator_service=svc2)
        assert parser2.read_games() == []

    def test_platform_metadata_is_populated(self) -> None:
        svc = MagicMock()
        svc.get_games_for_steam_export.return_value = [
            GameForExport(
                name="Tetris",
                rom_path="/roms/gb/Tetris.gb",
                system="gb",
                emulator_name="RetroArch",
                launch_command="flatpak run org.libretro.RetroArch -L gambatte_libretro /roms/gb/Tetris.gb",
                system_display="Game Boy",
            )
        ]
        parser = RomParser(emulator_service=svc)
        games = parser.read_games()
        meta = dict(games[0].platform_metadata)
        assert meta["emulator"] == "RetroArch"
        assert meta["system"] == "gb"
        assert meta["rom_file"] == "Tetris.gb"
        assert meta["rom_extension"] == ".gb"
