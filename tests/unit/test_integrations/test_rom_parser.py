"""Tests for ROM parser and emulator configuration."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.integrations.external_games.emulator_config import (
    EMUDECK_ROM_DIRS,
    EMULATORS,
    SYSTEM_EMULATORS,
    EmulatorDef,
)
from src.integrations.external_games.models import get_collection_emoji
from src.integrations.external_games.rom_parser import RomParser

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def parser() -> RomParser:
    """Create a fresh RomParser instance."""
    return RomParser()


@pytest.fixture()
def eden_def() -> EmulatorDef:
    """Eden emulator definition for testing."""
    return EmulatorDef(
        name="Eden",
        system="switch",
        system_display="Nintendo Switch",
        extensions=(".nsp", ".xci", ".nca"),
        exe_patterns=(
            "Eden.AppImage",
            "eden.AppImage",
            "Eden-Linux-*.AppImage",
        ),
        launch_template='"{exe}" "{rom}"',
    )


@pytest.fixture()
def dolphin_def() -> EmulatorDef:
    """Dolphin GC emulator definition for testing."""
    return EmulatorDef(
        name="Dolphin (GC)",
        system="gc",
        system_display="Nintendo GameCube",
        extensions=(".iso", ".gcz", ".rvz", ".gcm", ".ciso"),
        exe_patterns=("dolphin-emu",),
        flatpak_id="org.DolphinEmu.dolphin-emu",
        launch_template='"{exe}" --exec="{rom}"',
    )


@pytest.fixture()
def retroarch_snes_def() -> EmulatorDef:
    """RetroArch SNES definition for testing."""
    return EmulatorDef(
        name="RetroArch (SNES)",
        system="snes",
        system_display="Super Nintendo",
        extensions=(".sfc", ".smc", ".fig"),
        exe_patterns=("retroarch",),
        flatpak_id="org.libretro.RetroArch",
        launch_template='"{exe}" -L snes9x_libretro "{rom}"',
    )


# ===========================================================================
# EmulatorConfig Tests
# ===========================================================================


class TestEmulatorConfig:
    """Tests for emulator_config.py data structures."""

    def test_emulators_tuple_not_empty(self) -> None:
        """EMULATORS registry contains definitions."""
        assert len(EMULATORS) >= 16

    def test_system_emulators_built_correctly(self) -> None:
        """SYSTEM_EMULATORS maps system IDs to emulator lists."""
        assert "switch" in SYSTEM_EMULATORS
        assert len(SYSTEM_EMULATORS["switch"]) >= 4  # Eden, Citron, Ryujinx, Yuzu

    def test_emudeck_rom_dirs_has_all_systems(self) -> None:
        """EMUDECK_ROM_DIRS covers expected systems."""
        expected = {"switch", "wiiu", "3ds", "nds", "gc", "wii", "n64", "snes", "nes", "gba", "gb", "psp", "dos"}
        assert expected.issubset(set(EMUDECK_ROM_DIRS.keys()))

    def test_emulator_def_frozen(self) -> None:
        """EmulatorDef is immutable."""
        emu = EMULATORS[0]
        with pytest.raises(AttributeError):
            emu.name = "Modified"  # type: ignore[misc]

    def test_eden_is_first_switch_emulator(self) -> None:
        """Eden has highest priority for Switch (first in SYSTEM_EMULATORS)."""
        switch_emus = SYSTEM_EMULATORS["switch"]
        assert switch_emus[0].name == "Eden"


# ===========================================================================
# Emulator Detection Tests
# ===========================================================================


class TestEmulatorDetection:
    """Tests for emulator detection logic."""

    def test_find_emulator_appimage(self, tmp_path: Path, parser: RomParser) -> None:
        """Detect Eden AppImage in common location."""
        apps_dir = tmp_path / ".local" / "share" / "applications"
        apps_dir.mkdir(parents=True)
        eden = apps_dir / "Eden.AppImage"
        eden.touch()
        eden.chmod(0o755)

        eden_def = EMULATORS[0]  # Eden
        with (
            patch.object(
                type(parser),
                "APPIMAGE_DIRS",
                (str(apps_dir),),
            ),
            patch.object(
                type(parser),
                "EMUDECK_LAUNCHER_DIRS",
                (),
            ),
        ):
            result = parser._find_emulator(eden_def)

        assert result == eden

    def test_find_emulator_versioned_appimage(self, tmp_path: Path, parser: RomParser) -> None:
        """Detect versioned Eden AppImage via glob."""
        apps_dir = tmp_path / "Applications"
        apps_dir.mkdir()
        eden = apps_dir / "Eden-Linux-v0.2.0-rc1-legacy-clang-pgo.AppImage"
        eden.touch()
        eden.chmod(0o755)

        eden_def = EMULATORS[0]  # Eden
        with (
            patch.object(
                type(parser),
                "APPIMAGE_DIRS",
                (str(apps_dir),),
            ),
            patch.object(
                type(parser),
                "EMUDECK_LAUNCHER_DIRS",
                (),
            ),
        ):
            result = parser._find_emulator(eden_def)

        assert result is not None
        assert "Eden-Linux" in result.name

    def test_find_emulator_flatpak(self, parser: RomParser) -> None:
        """Detect Flatpak emulator (mocked subprocess)."""
        dolphin_def = EmulatorDef(
            name="Dolphin (GC)",
            system="gc",
            system_display="Nintendo GameCube",
            extensions=(".iso",),
            exe_patterns=("dolphin-emu",),
            flatpak_id="org.DolphinEmu.dolphin-emu",
            launch_template='"{exe}" --exec="{rom}"',
        )

        mock_result = MagicMock()
        mock_result.returncode = 0

        with (
            patch("shutil.which", return_value="/usr/bin/flatpak"),
            patch("subprocess.run", return_value=mock_result),
            patch.object(type(parser), "EMUDECK_LAUNCHER_DIRS", ()),
        ):
            result = parser._find_emulator(dolphin_def)

        assert result == Path("/flatpak/org.DolphinEmu.dolphin-emu")

    def test_find_emulator_emudeck_launcher(self, tmp_path: Path, parser: RomParser) -> None:
        """Detect EmuDeck launcher script."""
        launcher_dir = tmp_path / "Emulation" / "tools" / "launchers"
        launcher_dir.mkdir(parents=True)
        script = launcher_dir / "cemu.sh"
        script.write_text('#!/bin/bash\nexec cemu "$@"')
        script.chmod(0o755)

        cemu_def = EmulatorDef(
            name="Cemu",
            system="wiiu",
            system_display="Nintendo Wii U",
            extensions=(".wud",),
            exe_patterns=("Cemu",),
            launch_template='"{exe}" -g "{rom}"',
            emudeck_launcher="cemu.sh",
        )

        with patch.object(
            type(parser),
            "EMUDECK_LAUNCHER_DIRS",
            (str(launcher_dir),),
        ):
            result = parser._find_emulator(cemu_def)

        assert result == script

    def test_find_emulator_not_found(self, parser: RomParser) -> None:
        """Return None when emulator is not installed."""
        eden_def = EMULATORS[0]
        with (
            patch.object(type(parser), "APPIMAGE_DIRS", ()),
            patch.object(type(parser), "EMUDECK_LAUNCHER_DIRS", ()),
            patch("shutil.which", return_value=None),
        ):
            result = parser._find_emulator(eden_def)

        assert result is None

    def test_find_emulator_priority_emudeck_over_flatpak(self, tmp_path: Path, parser: RomParser) -> None:
        """EmuDeck launcher takes priority over Flatpak."""
        launcher_dir = tmp_path / "launchers"
        launcher_dir.mkdir()
        script = launcher_dir / "ryujinx.sh"
        script.write_text("#!/bin/bash\n")
        script.chmod(0o755)

        ryujinx_def = EmulatorDef(
            name="Ryujinx",
            system="switch",
            system_display="Nintendo Switch",
            extensions=(".nsp",),
            exe_patterns=("Ryujinx",),
            flatpak_id="org.ryujinx.Ryujinx",
            launch_template='"{exe}" "{rom}"',
            emudeck_launcher="ryujinx.sh",
        )

        mock_result = MagicMock()
        mock_result.returncode = 0

        with (
            patch.object(type(parser), "EMUDECK_LAUNCHER_DIRS", (str(launcher_dir),)),
            patch("shutil.which", return_value="/usr/bin/flatpak"),
            patch("subprocess.run", return_value=mock_result),
        ):
            result = parser._find_emulator(ryujinx_def)

        # EmuDeck script should win over Flatpak
        assert result == script

    def test_find_emulator_priority_applications_over_downloads(self, tmp_path: Path, parser: RomParser) -> None:
        """AppImage in ~/Applications/ beats same AppImage in ~/Downloads/."""
        apps_dir = tmp_path / "Applications"
        apps_dir.mkdir()
        apps_eden = apps_dir / "Eden.AppImage"
        apps_eden.touch()
        apps_eden.chmod(0o755)

        downloads_dir = tmp_path / "Downloads"
        downloads_dir.mkdir()
        dl_eden = downloads_dir / "Eden.AppImage"
        dl_eden.touch()
        dl_eden.chmod(0o755)

        eden_def = EMULATORS[0]
        with (
            patch.object(
                type(parser),
                "APPIMAGE_DIRS",
                (str(apps_dir), str(downloads_dir)),
            ),
            patch.object(
                type(parser),
                "EMUDECK_LAUNCHER_DIRS",
                (),
            ),
        ):
            result = parser._find_emulator(eden_def)

        assert result == apps_eden

    def test_find_emulator_falls_back_to_downloads(self, tmp_path: Path, parser: RomParser) -> None:
        """If AppImage only exists in ~/Downloads/, still find it."""
        downloads_dir = tmp_path / "Downloads"
        downloads_dir.mkdir()
        dl_eden = downloads_dir / "Eden.AppImage"
        dl_eden.touch()
        dl_eden.chmod(0o755)

        eden_def = EMULATORS[0]
        with (
            patch.object(
                type(parser),
                "APPIMAGE_DIRS",
                (str(tmp_path / "Applications"), str(downloads_dir)),
            ),
            patch.object(
                type(parser),
                "EMUDECK_LAUNCHER_DIRS",
                (),
            ),
        ):
            result = parser._find_emulator(eden_def)

        assert result == dl_eden


# ===========================================================================
# ROM Scan Tests
# ===========================================================================


class TestRomScan:
    """Tests for ROM file scanning."""

    def test_scan_rom_files_switch(self, tmp_path: Path) -> None:
        """Find .nsp and .xci files in switch directory."""
        switch_dir = tmp_path / "roms" / "switch"
        switch_dir.mkdir(parents=True)
        (switch_dir / "Metroid Dread.nsp").touch()
        (switch_dir / "Zelda TOTK.xci").touch()
        (switch_dir / "readme.txt").touch()  # Should be ignored

        roms = RomParser._scan_rom_files(switch_dir, (".nsp", ".xci", ".nca"))

        assert len(roms) == 2
        names = [r.name for r in roms]
        assert "Metroid Dread.nsp" in names
        assert "Zelda TOTK.xci" in names

    def test_scan_rom_files_empty_dir(self, tmp_path: Path) -> None:
        """Empty ROM directory returns empty list."""
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()

        roms = RomParser._scan_rom_files(empty_dir, (".nsp",))
        assert roms == []

    def test_scan_rom_files_permission_error(self, tmp_path: Path) -> None:
        """Unreadable directory is handled gracefully."""
        restricted = tmp_path / "restricted"
        restricted.mkdir()
        restricted.chmod(0o000)

        roms = RomParser._scan_rom_files(restricted, (".nsp",))
        assert roms == []

        # Cleanup
        restricted.chmod(0o755)


# ===========================================================================
# Name Extraction Tests
# ===========================================================================


class TestNameExtraction:
    """Tests for ROM name cleaning."""

    def test_extract_name_simple(self) -> None:
        """Simple filename without tags."""
        assert RomParser._extract_game_name(Path("Metroid Dread.nsp")) == "Metroid Dread"

    def test_extract_name_title_id(self) -> None:
        """Remove title ID from filename."""
        result = RomParser._extract_game_name(Path("Super Mario Odyssey [01006A800016E000][v0].nsp"))
        assert result == "Super Mario Odyssey"

    def test_extract_name_region(self) -> None:
        """Remove region code."""
        result = RomParser._extract_game_name(Path("Zelda BOTW (USA) (v1.6).xci"))
        assert result == "Zelda BOTW"

    def test_extract_name_complex(self) -> None:
        """Multiple tags removed."""
        result = RomParser._extract_game_name(Path("Animal Crossing [01006F8002326000][v131072] (USA).nsp"))
        assert result == "Animal Crossing"

    def test_extract_name_only_tags(self) -> None:
        """Filename with only tags falls back to stem."""
        result = RomParser._extract_game_name(Path("[01006A800016E000][v0].nsp"))
        assert result == "[01006A800016E000][v0]"


# ===========================================================================
# Launch Command Tests
# ===========================================================================


class TestLaunchCommand:
    """Tests for launch command building."""

    def test_build_launch_command_appimage(self, eden_def: EmulatorDef) -> None:
        """AppImage launch: exe + rom as argument."""
        exe = Path("/home/user/.local/share/applications/Eden.AppImage")
        rom = Path("/mnt/volume/Emulation/roms/switch/Metroid Dread.nsp")

        result = RomParser._build_launch_command(eden_def, exe, rom)

        assert '"/home/user/.local/share/applications/Eden.AppImage"' in result
        assert '"/mnt/volume/Emulation/roms/switch/Metroid Dread.nsp"' in result

    def test_build_launch_command_flatpak_with_args(self, dolphin_def: EmulatorDef) -> None:
        """Flatpak launch preserves emulator-specific args from launch_template."""
        exe = Path("/flatpak/org.DolphinEmu.dolphin-emu")
        rom = Path("/home/user/roms/gc/Metroid Prime.iso")

        result = RomParser._build_launch_command(dolphin_def, exe, rom)

        assert result.startswith("flatpak run org.DolphinEmu.dolphin-emu")
        assert "--exec=" in result
        assert "Metroid Prime.iso" in result

    def test_build_launch_command_flatpak_retroarch(self, retroarch_snes_def: EmulatorDef) -> None:
        """Flatpak RetroArch preserves -L core argument."""
        exe = Path("/flatpak/org.libretro.RetroArch")
        rom = Path("/home/user/roms/snes/Super Metroid.sfc")

        result = RomParser._build_launch_command(retroarch_snes_def, exe, rom)

        assert result.startswith("flatpak run org.libretro.RetroArch")
        assert "-L snes9x_libretro" in result
        assert "Super Metroid.sfc" in result

    def test_build_launch_command_flatpak_simple(self, eden_def: EmulatorDef) -> None:
        """Flatpak with simple template uses fallback."""
        exe = Path("/flatpak/dev.eden_emu.eden")
        rom = Path("/home/user/roms/switch/Zelda.nsp")

        result = RomParser._build_launch_command(eden_def, exe, rom)

        assert result.startswith("flatpak run dev.eden_emu.eden")
        assert "Zelda.nsp" in result

    def test_build_launch_command_emudeck_script(self) -> None:
        """EmuDeck launcher script: script + rom."""
        cemu_def = EmulatorDef(
            name="Cemu",
            system="wiiu",
            system_display="Nintendo Wii U",
            extensions=(".wud",),
            exe_patterns=("Cemu",),
            launch_template='"{exe}" -g "{rom}"',
            emudeck_launcher="cemu.sh",
        )
        exe = Path("/mnt/volume/Emulation/tools/launchers/cemu.sh")
        rom = Path("/mnt/volume/Emulation/roms/wiiu/MarioKart8.wud")

        result = RomParser._build_launch_command(cemu_def, exe, rom)

        assert "-g" in result
        assert "MarioKart8.wud" in result
        assert "cemu.sh" in result

    def test_build_launch_command_retroarch_native(self) -> None:
        """Native RetroArch: exe + -L core + rom."""
        ra_def = EmulatorDef(
            name="RetroArch (SNES)",
            system="snes",
            system_display="Super Nintendo",
            extensions=(".sfc",),
            exe_patterns=("retroarch",),
            launch_template='"{exe}" -L snes9x_libretro "{rom}"',
        )
        exe = Path("/usr/bin/retroarch")
        rom = Path("/home/user/roms/snes/DonkeyKong.sfc")

        result = RomParser._build_launch_command(ra_def, exe, rom)

        assert '"/usr/bin/retroarch"' in result
        assert "-L snes9x_libretro" in result
        assert '"' in result  # ROM path should be quoted


# ===========================================================================
# Integration Tests
# ===========================================================================


class TestReadGames:
    """Tests for the full read_games pipeline."""

    def test_read_games_full_pipeline(self, tmp_path: Path, parser: RomParser) -> None:
        """Full pipeline: detect emulator + scan ROMs + create ExternalGames."""
        # Set up ROM directory
        rom_base = tmp_path / "Emulation" / "roms"
        switch_dir = rom_base / "switch"
        switch_dir.mkdir(parents=True)
        (switch_dir / "Metroid Dread.nsp").touch()

        # Set up emulator
        apps_dir = tmp_path / "Applications"
        apps_dir.mkdir()
        eden = apps_dir / "Eden.AppImage"
        eden.touch()
        eden.chmod(0o755)

        with (
            patch(
                "src.integrations.external_games.rom_parser.ROM_SEARCH_PATHS",
                (str(rom_base),),
            ),
            patch.object(
                type(parser),
                "APPIMAGE_DIRS",
                (str(apps_dir),),
            ),
            patch.object(
                type(parser),
                "EMUDECK_LAUNCHER_DIRS",
                (),
            ),
            patch("shutil.which", return_value=None),
        ):
            games = parser.read_games()

        assert len(games) == 1
        game = games[0]
        assert game.name == "Metroid Dread"
        assert game.platform == "Emulation (Nintendo Switch)"
        assert game.platform_app_id == "rom:switch:Metroid Dread.nsp"
        assert game.executable is not None and str(eden) in game.executable
        assert "Metroid Dread.nsp" in game.launch_command

        # Check metadata
        meta = dict(game.platform_metadata)
        assert meta["emulator"] == "Eden"
        assert meta["system"] == "switch"
        assert meta["rom_file"] == "Metroid Dread.nsp"
        assert meta["rom_extension"] == ".nsp"

    def test_read_games_no_emulators(self, tmp_path: Path, parser: RomParser) -> None:
        """No emulators detected returns empty list."""
        rom_base = tmp_path / "roms"
        switch_dir = rom_base / "switch"
        switch_dir.mkdir(parents=True)
        (switch_dir / "game.nsp").touch()

        with (
            patch(
                "src.integrations.external_games.rom_parser.ROM_SEARCH_PATHS",
                (str(rom_base),),
            ),
            patch.object(
                type(parser),
                "APPIMAGE_DIRS",
                (),
            ),
            patch.object(
                type(parser),
                "EMUDECK_LAUNCHER_DIRS",
                (),
            ),
            patch("shutil.which", return_value=None),
        ):
            games = parser.read_games()

        assert games == []

    def test_read_games_no_roms(self, tmp_path: Path, parser: RomParser) -> None:
        """Emulators but no ROM directories returns empty list."""
        with patch(
            "src.integrations.external_games.rom_parser.ROM_SEARCH_PATHS",
            (str(tmp_path / "nonexistent"),),
        ):
            games = parser.read_games()

        # No ROM dirs found -> early return (or no emulators if also patched)
        assert games == []

    def test_is_available_with_roms(self, tmp_path: Path, parser: RomParser) -> None:
        """is_available returns True when ROM dirs exist with files."""
        rom_dir = tmp_path / "roms"
        rom_dir.mkdir()
        (rom_dir / "game.nsp").touch()

        with patch(
            "src.integrations.external_games.rom_parser.ROM_SEARCH_PATHS",
            (str(rom_dir),),
        ):
            assert parser.is_available() is True

    def test_is_available_empty(self, parser: RomParser) -> None:
        """is_available returns False when no ROM dirs exist."""
        with patch(
            "src.integrations.external_games.rom_parser.ROM_SEARCH_PATHS",
            ("/nonexistent/path/that/does/not/exist",),
        ):
            assert parser.is_available() is False

    def test_platform_name(self, parser: RomParser) -> None:
        """Platform name is correct."""
        assert parser.platform_name() == "Emulation (ROMs)"


# ===========================================================================
# Collection Emoji Tests
# ===========================================================================


class TestCollectionEmoji:
    """Tests for collection emoji mapping."""

    def test_get_collection_emoji_known(self) -> None:
        """Known platform returns emoji via t()."""
        with patch("src.integrations.external_games.models.t", return_value="🔴"):
            result = get_collection_emoji("Nintendo Switch")
        assert result == "🔴"

    def test_get_collection_emoji_unknown(self) -> None:
        """Unknown platform returns empty string."""
        result = get_collection_emoji("Unknown Platform XYZ")
        assert result == ""

    def test_collection_emoji_keys_cover_rom_systems(self) -> None:
        """All ROM system display names have emoji mappings."""
        from src.integrations.external_games.models import _COLLECTION_EMOJI_KEYS

        # All system_display values from EmulatorDef should have mappings
        for emu in EMULATORS:
            assert emu.system_display in _COLLECTION_EMOJI_KEYS, f"Missing emoji mapping for {emu.system_display}"


# ===========================================================================
# Collection Name Extraction Tests
# ===========================================================================


class TestCollectionNameForPlatform:
    """Tests for clean collection name extraction."""

    def test_emulation_platform_extracted(self) -> None:
        """Emulation wrapper is stripped."""
        from src.ui.dialogs.external_games_dialog import ExternalGamesDialog

        assert ExternalGamesDialog._collection_name_for_platform("Emulation (Nintendo Switch)") == "Nintendo Switch"

    def test_non_emulation_platform_unchanged(self) -> None:
        """Non-emulation platforms are returned as-is."""
        from src.ui.dialogs.external_games_dialog import ExternalGamesDialog

        assert ExternalGamesDialog._collection_name_for_platform("Heroic (Epic)") == "Heroic (Epic)"
