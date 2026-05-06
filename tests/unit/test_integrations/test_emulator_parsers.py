"""Tests for emulator config parsers (Phase B)."""

from __future__ import annotations

import json
from pathlib import Path

from steam_library_manager.integrations.external_games.emulator_parsers import (
    AzaharParser,
    CemuParser,
    DolphinParser,
    EdenParser,
    EmuDeckHintProvider,
    PPSSPPParser,
    RetroArchParser,
    RyujinxParser,
)
from steam_library_manager.integrations.external_games.emulator_parsers.protocol import (
    EmulatorConfigParser,
    GameRef,
    InstalledEmulator,
)


class TestEdenParser:
    def test_reads_gamedirs_from_qt_ini(self, tmp_path: Path) -> None:
        cfg = tmp_path / "qt-config.ini"
        cfg.write_text(
            "[UI]\n"
            "Paths\\gamedirs\\1\\path=SDMC\n"
            "Paths\\gamedirs\\1\\path\\default=true\n"
            "Paths\\gamedirs\\2\\path=/mnt/games/Emulation/roms/switch\n"
            "Paths\\gamedirs\\2\\path\\default=false\n"
            "Paths\\gamedirs\\3\\path=~/Roms/Switch\n"
            "Paths\\gamedirs\\3\\path\\default=false\n"
        )
        parser = EdenParser(config_path=cfg)
        dirs = parser.get_game_dirs()
        # SDMC is internal marker, should be filtered out
        assert Path("/mnt/games/Emulation/roms/switch") in dirs
        assert any(str(d).endswith("Roms/Switch") for d in dirs)
        assert all("SDMC" not in str(d) for d in dirs)

    def test_filters_internal_markers(self, tmp_path: Path) -> None:
        cfg = tmp_path / "qt-config.ini"
        cfg.write_text(
            "Paths\\gamedirs\\1\\path=SDMC\n" "Paths\\gamedirs\\2\\path=UserNAND\n" "Paths\\gamedirs\\3\\path=SysNAND\n"
        )
        parser = EdenParser(config_path=cfg)
        assert parser.get_game_dirs() == []

    def test_missing_config_returns_empty(self, tmp_path: Path) -> None:
        parser = EdenParser(config_path=tmp_path / "nonexistent.ini")
        assert parser.get_game_dirs() == []

    def test_systems(self) -> None:
        assert EdenParser().systems == ("switch",)
        assert EdenParser().name == "Eden"


class TestRyujinxParser:
    def test_reads_game_dirs_from_json(self, tmp_path: Path) -> None:
        cfg = tmp_path / "Config.json"
        cfg.write_text(json.dumps({"game_dirs": ["/mnt/roms/switch", "/home/user/switch"]}))
        parser = RyujinxParser(config_path=cfg)
        dirs = parser.get_game_dirs()
        assert dirs == [Path("/mnt/roms/switch"), Path("/home/user/switch")]

    def test_malformed_json_returns_empty(self, tmp_path: Path) -> None:
        cfg = tmp_path / "Config.json"
        cfg.write_text("{ not json")
        assert RyujinxParser(config_path=cfg).get_game_dirs() == []

    def test_missing_key_returns_empty(self, tmp_path: Path) -> None:
        cfg = tmp_path / "Config.json"
        cfg.write_text(json.dumps({"other_key": []}))
        assert RyujinxParser(config_path=cfg).get_game_dirs() == []


class TestCemuParser:
    def test_reads_gamepaths_from_xml(self, tmp_path: Path) -> None:
        cfg = tmp_path / "settings.xml"
        cfg.write_text(
            "<?xml version='1.0' encoding='UTF-8'?>\n"
            "<content>\n"
            "  <GamePaths>\n"
            "    <Entry>/mnt/roms/wiiu</Entry>\n"
            "    <Entry>/home/user/wiiu</Entry>\n"
            "  </GamePaths>\n"
            "</content>\n"
        )
        parser = CemuParser(config_path=cfg)
        dirs = parser.get_game_dirs()
        assert Path("/mnt/roms/wiiu") in dirs
        assert Path("/home/user/wiiu") in dirs

    def test_empty_gamepaths(self, tmp_path: Path) -> None:
        cfg = tmp_path / "settings.xml"
        cfg.write_text("<content><GamePaths/></content>")
        assert CemuParser(config_path=cfg).get_game_dirs() == []

    def test_malformed_xml_returns_empty(self, tmp_path: Path) -> None:
        cfg = tmp_path / "settings.xml"
        cfg.write_text("<broken")
        assert CemuParser(config_path=cfg).get_game_dirs() == []


class TestDolphinParser:
    def test_reads_isopaths_from_ini(self, tmp_path: Path) -> None:
        cfg = tmp_path / "Dolphin.ini"
        cfg.write_text(
            "[General]\n"
            "RecursiveISOPaths = True\n"
            "ISOPath0 = /mnt/roms/gc\n"
            "ISOPaths = 2\n"
            "ISOPath1 = /mnt/roms/wii\n"
        )
        parser = DolphinParser(config_path=cfg)
        dirs = parser.get_game_dirs()
        assert Path("/mnt/roms/gc") in dirs
        assert Path("/mnt/roms/wii") in dirs

    def test_no_general_section(self, tmp_path: Path) -> None:
        cfg = tmp_path / "Dolphin.ini"
        cfg.write_text("[Other]\nfoo = bar\n")
        assert DolphinParser(config_path=cfg).get_game_dirs() == []

    def test_supports_gc_and_wii(self) -> None:
        assert DolphinParser().systems == ("gc", "wii")


class TestAzaharParser:
    def test_uses_yuzu_qt_schema(self, tmp_path: Path) -> None:
        cfg = tmp_path / "qt-config.ini"
        cfg.write_text("Paths\\gamedirs\\1\\path=/mnt/roms/3ds\n" "Paths\\gamedirs\\1\\path\\default=false\n")
        assert AzaharParser(config_path=cfg).get_game_dirs() == [Path("/mnt/roms/3ds")]


class TestRetroArchParser:
    def test_reads_playlist_items(self, tmp_path: Path) -> None:
        playlists = tmp_path
        pl = playlists / "Nintendo - Game Boy.lpl"
        pl.write_text(
            json.dumps(
                {
                    "items": [
                        {"path": "/mnt/roms/gb/Tetris.gb", "label": "Tetris"},
                        {"path": "/mnt/roms/gb/Pokemon Red.gb", "label": "Pokemon Red"},
                    ]
                }
            )
        )
        parser = RetroArchParser(playlists_dir=playlists)
        games = parser.get_known_games()
        assert len(games) == 2
        assert all(g.system == "gb" for g in games)
        assert {g.name for g in games} == {"Tetris", "Pokemon Red"}

    def test_unknown_playlist_skipped(self, tmp_path: Path) -> None:
        playlists = tmp_path
        pl = playlists / "Some Random System.lpl"
        pl.write_text(json.dumps({"items": [{"path": "/x.rom", "label": "X"}]}))
        assert RetroArchParser(playlists_dir=playlists).get_known_games() == []

    def test_game_dirs_derived_from_known(self, tmp_path: Path) -> None:
        playlists = tmp_path
        pl = playlists / "Nintendo - Game Boy.lpl"
        pl.write_text(json.dumps({"items": [{"path": "/mnt/roms/gb/A.gb", "label": "A"}]}))
        parser = RetroArchParser(playlists_dir=playlists)
        assert parser.get_game_dirs() == [Path("/mnt/roms/gb")]


class TestPPSSPPParser:
    def test_reads_recent_isos(self, tmp_path: Path) -> None:
        cfg = tmp_path / "ppsspp.ini"
        cfg.write_text(
            "[Recent]\n"
            "FileName1 = /mnt/roms/psp/Game1.iso\n"
            "FileName2 = /mnt/roms/psp/Game2.iso\n"
            "FileName3 = /home/user/psp/Game3.iso\n"
        )
        dirs = PPSSPPParser(config_path=cfg).get_game_dirs()
        assert "/mnt/roms/psp" in [str(d) for d in dirs]
        assert "/home/user/psp" in [str(d) for d in dirs]


class TestEmuDeckHintProvider:
    def test_handles_concatenation_bug(self, tmp_path: Path) -> None:
        # simulate the EmuDeck bug: emulationPath="/mnt/games/Emulation"/Emulation
        # the bash-evaluated form would be /mnt/games/Emulation/Emulation (broken)
        emu_root = tmp_path / "Emulation"
        emu_root.mkdir()
        (emu_root / "roms" / "switch").mkdir(parents=True)

        settings = tmp_path / "settings.sh"
        settings.write_text(
            'emulationPath="%s"/Emulation\n'  # <- the buggy line
            'romsPath="%s"/Emulation/roms\n' % (str(emu_root), str(emu_root))
        )
        provider = EmuDeckHintProvider(settings_paths=(settings,))
        assert provider.get_emulation_path() == emu_root
        assert provider.get_rom_dir("switch") == emu_root / "roms" / "switch"

    def test_clean_settings(self, tmp_path: Path) -> None:
        emu = tmp_path / "Emulation"
        (emu / "roms" / "gba").mkdir(parents=True)
        settings = tmp_path / "settings.sh"
        settings.write_text('emulationPath="%s"\n' % emu)
        provider = EmuDeckHintProvider(settings_paths=(settings,))
        assert provider.get_emulation_path() == emu
        assert provider.get_rom_dir("gba") == emu / "roms" / "gba"

    def test_returns_none_if_path_does_not_exist(self, tmp_path: Path) -> None:
        settings = tmp_path / "settings.sh"
        settings.write_text('emulationPath="/nonexistent/path"\n')
        provider = EmuDeckHintProvider(settings_paths=(settings,))
        assert provider.get_emulation_path() is None

    def test_get_all_rom_dirs(self, tmp_path: Path) -> None:
        emu = tmp_path / "Emulation"
        (emu / "roms" / "switch").mkdir(parents=True)
        (emu / "roms" / "gba").mkdir(parents=True)
        settings = tmp_path / "settings.sh"
        settings.write_text('emulationPath="%s"\n' % emu)
        result = EmuDeckHintProvider(settings_paths=(settings,)).get_all_rom_dirs()
        assert "switch" in result
        assert "gba" in result
        assert "n64" not in result  # subdir does not exist

    def test_no_settings_file_means_unavailable(self, tmp_path: Path) -> None:
        provider = EmuDeckHintProvider(settings_paths=(tmp_path / "missing.sh",))
        assert provider.is_available() is False
        assert provider.get_emulation_path() is None


class TestProtocolConformance:
    def test_all_parsers_implement_protocol(self) -> None:
        # runtime_checkable Protocol allows isinstance() checks
        for parser_cls in (
            EdenParser,
            RyujinxParser,
            CemuParser,
            DolphinParser,
            AzaharParser,
            RetroArchParser,
            PPSSPPParser,
        ):
            assert isinstance(parser_cls(), EmulatorConfigParser), parser_cls.__name__


class TestDataclasses:
    def test_game_ref(self) -> None:
        g = GameRef(name="Test", path=Path("/x"), system="switch")
        assert g.name == "Test"
        assert g.path == Path("/x")
        assert g.system == "switch"

    def test_installed_emulator(self) -> None:
        e = InstalledEmulator(
            name="Eden",
            systems=("switch",),
            executable=Path("/usr/bin/eden"),
            source="system",
            game_dirs=(Path("/x"),),
        )
        assert e.name == "Eden"
        assert e.systems == ("switch",)
