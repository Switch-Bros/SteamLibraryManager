"""Tests for EmulatorService (orchestrator)."""

from __future__ import annotations

from pathlib import Path

import pytest

from steam_library_manager.core.db import Database
from steam_library_manager.integrations.external_games.emulator_parsers.protocol import GameRef
from steam_library_manager.services.emulator_service import (
    EmulatorService,
)


class FakeParser:
    """Configurable stand-in for an emulator config parser."""

    def __init__(
        self,
        name: str,
        systems: tuple[str, ...],
        installed: bool = True,
        executable: Path | None = None,
        game_dirs: list[Path] | None = None,
        known_games: list[GameRef] | None = None,
    ) -> None:
        self._name = name
        self._systems = systems
        self._installed = installed
        self._exe = executable
        self._dirs = game_dirs or []
        self._known = known_games or []

    @property
    def name(self) -> str:
        return self._name

    @property
    def systems(self) -> tuple[str, ...]:
        return self._systems

    def is_installed(self) -> bool:
        return self._installed

    def get_executable(self) -> Path | None:
        return self._exe

    def get_game_dirs(self) -> list[Path]:
        return list(self._dirs)

    def get_known_games(self) -> list[GameRef]:
        return list(self._known)


class FakeEmuDeck:
    def __init__(self, available: bool = False, rom_dirs: dict[str, Path] | None = None) -> None:
        self._available = available
        self._rom_dirs = rom_dirs or {}

    def is_available(self) -> bool:
        return self._available

    def get_rom_dir(self, system: str) -> Path | None:
        return self._rom_dirs.get(system)


@pytest.fixture
def db(tmp_path: Path) -> Database:
    return Database(tmp_path / "test.db")


@pytest.fixture
def switch_roms_dir(tmp_path: Path) -> Path:
    d = tmp_path / "roms" / "switch"
    d.mkdir(parents=True)
    (d / "Metroid Dread [v327680].nsp").touch()
    (d / "Zelda BOTW.xci").touch()
    return d


class TestDetectInstalled:
    def test_only_installed_returned(self, db: Database) -> None:
        parsers = [
            FakeParser("Eden", ("switch",), installed=True, executable=Path("/usr/bin/eden")),
            FakeParser("Cemu", ("wiiu",), installed=False),
        ]
        svc = EmulatorService(db, parsers=parsers, emudeck_hint=FakeEmuDeck())
        result = svc.detect_installed_emulators()
        assert len(result) == 1
        assert result[0].name == "Eden"

    def test_disabled_emulators_still_detected_but_skipped_in_discover(
        self, db: Database, switch_roms_dir: Path
    ) -> None:
        parser = FakeParser(
            "Eden",
            ("switch",),
            installed=True,
            executable=Path("/flatpak/dev.eden_emu.eden"),
            game_dirs=[switch_roms_dir],
        )
        svc = EmulatorService(db, parsers=[parser], emudeck_hint=FakeEmuDeck())
        # detect still picks it up
        assert len(svc.detect_installed_emulators()) == 1
        # but if disabled, discover skips it
        db.set_emulator_enabled("Eden", False)
        result = svc.discover_libraries()
        assert result.roms_found == 0


class TestDiscoverLibraries:
    def test_finds_roms_from_parser_dirs(self, db: Database, switch_roms_dir: Path) -> None:
        parser = FakeParser(
            "Eden",
            ("switch",),
            installed=True,
            executable=Path("/flatpak/dev.eden_emu.eden"),
            game_dirs=[switch_roms_dir],
        )
        svc = EmulatorService(db, parsers=[parser], emudeck_hint=FakeEmuDeck())
        result = svc.discover_libraries()
        assert result.roms_found == 2
        assert result.systems == ["switch"]
        assert result.conflicts == []

    def test_finds_roms_via_emudeck_fallback(self, db: Database, switch_roms_dir: Path) -> None:
        # parser has no game_dirs, but EmuDeck hint provides one
        parser = FakeParser(
            "Eden",
            ("switch",),
            installed=True,
            executable=Path("/flatpak/dev.eden_emu.eden"),
            game_dirs=[],
        )
        emudeck = FakeEmuDeck(available=True, rom_dirs={"switch": switch_roms_dir})
        svc = EmulatorService(db, parsers=[parser], emudeck_hint=emudeck)
        result = svc.discover_libraries()
        assert result.roms_found == 2

    def test_uses_user_custom_game_dirs(self, db: Database, switch_roms_dir: Path) -> None:
        parser = FakeParser(
            "Eden",
            ("switch",),
            installed=True,
            executable=Path("/flatpak/dev.eden_emu.eden"),
            game_dirs=[],
        )
        db.add_custom_game_dir("Eden", str(switch_roms_dir))
        svc = EmulatorService(db, parsers=[parser], emudeck_hint=FakeEmuDeck())
        result = svc.discover_libraries()
        assert result.roms_found == 2

    def test_known_games_from_retroarch(self, db: Database, tmp_path: Path) -> None:
        rom = tmp_path / "Tetris.gb"
        rom.touch()
        parser = FakeParser(
            "RetroArch",
            ("gb",),
            installed=True,
            executable=Path("/flatpak/org.libretro.RetroArch"),
            known_games=[GameRef(name="Tetris", path=rom, system="gb")],
        )
        svc = EmulatorService(db, parsers=[parser], emudeck_hint=FakeEmuDeck())
        result = svc.discover_libraries()
        assert result.roms_found == 1

    def test_conflict_detected(self, db: Database, switch_roms_dir: Path) -> None:
        # Eden and Ryujinx both point to the same dir
        eden = FakeParser(
            "Eden",
            ("switch",),
            installed=True,
            executable=Path("/flatpak/dev.eden_emu.eden"),
            game_dirs=[switch_roms_dir],
        )
        ryujinx = FakeParser(
            "Ryujinx",
            ("switch",),
            installed=True,
            executable=Path("/flatpak/org.ryujinx.Ryujinx"),
            game_dirs=[switch_roms_dir],
        )
        svc = EmulatorService(db, parsers=[eden, ryujinx], emudeck_hint=FakeEmuDeck())
        result = svc.discover_libraries()
        assert result.roms_found == 2
        assert len(result.conflicts) == 2
        for c in result.conflicts:
            assert "Eden" in c.emulators and "Ryujinx" in c.emulators

    def test_priority_picks_eden_over_ryujinx(self, db: Database, switch_roms_dir: Path) -> None:
        # EMULATORS list has Eden before Ryujinx
        eden = FakeParser(
            "Eden",
            ("switch",),
            installed=True,
            executable=Path("/flatpak/dev.eden_emu.eden"),
            game_dirs=[switch_roms_dir],
        )
        ryujinx = FakeParser(
            "Ryujinx",
            ("switch",),
            installed=True,
            executable=Path("/flatpak/org.ryujinx.Ryujinx"),
            game_dirs=[switch_roms_dir],
        )
        svc = EmulatorService(db, parsers=[eden, ryujinx], emudeck_hint=FakeEmuDeck())
        svc.discover_libraries()
        games = db.get_emulator_games()
        for g in games:
            assert g["emulator_name"] == "Eden"

    def test_user_default_overrides_priority(self, db: Database, switch_roms_dir: Path) -> None:
        eden = FakeParser(
            "Eden",
            ("switch",),
            installed=True,
            executable=Path("/flatpak/dev.eden_emu.eden"),
            game_dirs=[switch_roms_dir],
        )
        ryujinx = FakeParser(
            "Ryujinx",
            ("switch",),
            installed=True,
            executable=Path("/flatpak/org.ryujinx.Ryujinx"),
            game_dirs=[switch_roms_dir],
        )
        svc = EmulatorService(db, parsers=[eden, ryujinx], emudeck_hint=FakeEmuDeck())
        svc.set_default_emulator_for_system("switch", "Ryujinx")
        svc.discover_libraries()
        games = db.get_emulator_games()
        for g in games:
            assert g["emulator_name"] == "Ryujinx"


class TestSteamExport:
    def test_export_includes_launch_command(self, db: Database, switch_roms_dir: Path) -> None:
        parser = FakeParser(
            "Eden",
            ("switch",),
            installed=True,
            executable=Path("/flatpak/dev.eden_emu.eden"),
            game_dirs=[switch_roms_dir],
        )
        svc = EmulatorService(db, parsers=[parser], emudeck_hint=FakeEmuDeck())
        svc.discover_libraries()
        games = svc.get_games_for_steam_export()
        assert len(games) == 2
        for g in games:
            assert g.system == "switch"
            assert g.emulator_name == "Eden"
            assert "flatpak run dev.eden_emu.eden" in g.launch_command
            assert g.rom_path in g.launch_command

    def test_export_excludes_already_exported(self, db: Database, switch_roms_dir: Path) -> None:
        parser = FakeParser(
            "Eden",
            ("switch",),
            installed=True,
            executable=Path("/flatpak/dev.eden_emu.eden"),
            game_dirs=[switch_roms_dir],
        )
        svc = EmulatorService(db, parsers=[parser], emudeck_hint=FakeEmuDeck())
        svc.discover_libraries()
        all_games = db.get_emulator_games()
        db.mark_emulator_game_added_to_steam(all_games[0]["rom_path"])
        unexported = svc.get_games_for_steam_export(only_unexported=True)
        assert len(unexported) == 1
        all_again = svc.get_games_for_steam_export(only_unexported=False)
        assert len(all_again) == 2


class TestLaunchCommand:
    def test_flatpak_launch(self, db: Database) -> None:
        parser = FakeParser(
            "Eden",
            ("switch",),
            installed=True,
            executable=Path("/flatpak/dev.eden_emu.eden"),
        )
        svc = EmulatorService(db, parsers=[parser], emudeck_hint=FakeEmuDeck())
        cmd = svc.build_launch_command("/roms/switch/Metroid.nsp", "Eden", "switch")
        assert cmd.startswith("flatpak run dev.eden_emu.eden")
        assert "Metroid.nsp" in cmd

    def test_system_binary_launch(self, db: Database) -> None:
        parser = FakeParser(
            "DOSBox",
            ("dos",),
            installed=True,
            executable=Path("/usr/bin/dosbox"),
        )
        svc = EmulatorService(db, parsers=[parser], emudeck_hint=FakeEmuDeck())
        cmd = svc.build_launch_command("/roms/dos/game.exe", "DOSBox", "dos")
        assert "/usr/bin/dosbox" in cmd
        assert "game.exe" in cmd

    def test_unknown_emulator_returns_empty(self, db: Database) -> None:
        svc = EmulatorService(db, parsers=[], emudeck_hint=FakeEmuDeck())
        assert svc.build_launch_command("/x.rom", "DoesNotExist", "switch") == ""


class TestNintendoUpdateCollapse:
    def test_switch_base_and_update_collapse_to_base(self, db: Database, tmp_path: Path) -> None:
        roms = tmp_path / "roms" / "switch"
        roms.mkdir(parents=True)
        (roms / "Metroid Dread [v0].nsp").touch()
        (roms / "Metroid Dread [v327680].nsp").touch()
        parser = FakeParser(
            "Eden",
            ("switch",),
            installed=True,
            executable=Path("/flatpak/dev.eden_emu.eden"),
            game_dirs=[roms],
        )
        svc = EmulatorService(db, parsers=[parser], emudeck_hint=FakeEmuDeck())
        result = svc.discover_libraries()
        # 2 ROMs found, but they collapse into 1 entry per (system, name)
        assert result.roms_found == 1
        rows = db.get_emulator_games()
        assert len(rows) == 1
        # the base game ([v0]) wins because it has the lowest version
        assert "[v0]" in rows[0]["rom_path"]

    def test_only_update_present_still_works(self, db: Database, tmp_path: Path) -> None:
        # if the user has *only* the update file, that is what we use
        roms = tmp_path / "roms" / "switch"
        roms.mkdir(parents=True)
        (roms / "Metroid Dread [v327680].nsp").touch()
        parser = FakeParser(
            "Eden",
            ("switch",),
            installed=True,
            executable=Path("/flatpak/dev.eden_emu.eden"),
            game_dirs=[roms],
        )
        svc = EmulatorService(db, parsers=[parser], emudeck_hint=FakeEmuDeck())
        result = svc.discover_libraries()
        assert result.roms_found == 1

    def test_snes_does_not_collapse_same_name(self, db: Database, tmp_path: Path) -> None:
        # for non-Nintendo-title systems, identical extracted names usually mean
        # genuinely different ROMs (e.g. regional variants) - keep them all
        roms = tmp_path / "roms" / "snes"
        roms.mkdir(parents=True)
        (roms / "Super Metroid.smc").touch()
        (roms / "Super Metroid (E) [!].smc").touch()
        # both strip to "Super Metroid"
        parser = FakeParser(
            "RetroArch",
            ("snes",),
            installed=True,
            executable=Path("/flatpak/org.libretro.RetroArch"),
            game_dirs=[roms],
        )
        svc = EmulatorService(db, parsers=[parser], emudeck_hint=FakeEmuDeck())
        result = svc.discover_libraries()
        assert result.roms_found == 2


class TestSettingsAPI:
    def test_add_remove_user_game_dir(self, db: Database, tmp_path: Path) -> None:
        svc = EmulatorService(db, parsers=[], emudeck_hint=FakeEmuDeck())
        svc.add_user_game_dir("Eden", tmp_path)
        s = db.get_emulator_settings("Eden")
        assert str(tmp_path) in s["custom_game_dirs"]
        svc.remove_user_game_dir("Eden", tmp_path)
        s = db.get_emulator_settings("Eden")
        assert str(tmp_path) not in s["custom_game_dirs"]

    def test_enable_disable(self, db: Database) -> None:
        svc = EmulatorService(db, parsers=[], emudeck_hint=FakeEmuDeck())
        svc.disable_emulator("Eden")
        assert db.get_emulator_settings("Eden")["enabled"] is False
        svc.enable_emulator("Eden")
        assert db.get_emulator_settings("Eden")["enabled"] is True
