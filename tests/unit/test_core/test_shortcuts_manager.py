"""Tests for ShortcutsManager and App-ID calculation.

Covers CRC32-based ID generation, shortcuts CRUD operations,
backup creation, and roundtrip with real VDF data.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from src.core.shortcuts_manager import (
    ShortcutsManager,
    SteamShortcut,
    generate_app_id,
    generate_preliminary_id,
    generate_short_app_id,
    generate_shortcut_id,
)

# Real shortcuts.vdf for integration tests
_REAL_SHORTCUTS = Path.home() / ".local" / "share" / "Steam" / "userdata" / "43925226" / "config" / "shortcuts.vdf"


# ---------------------------------------------------------------------------
# App-ID Calculation
# ---------------------------------------------------------------------------


class TestAppIDCalculation:
    """Tests for CRC32-based App-ID generation."""

    def test_generate_shortcut_id_is_negative(self) -> None:
        """Shortcut IDs are always negative signed int32."""
        result = generate_shortcut_id('"test"', "TestGame")
        assert result < 0

    def test_generate_shortcut_id_deterministic(self) -> None:
        """Same inputs always produce the same ID."""
        a = generate_shortcut_id('"test"', "Game")
        b = generate_shortcut_id('"test"', "Game")
        assert a == b

    def test_generate_shortcut_id_different_for_different_inputs(self) -> None:
        """Different inputs produce different IDs."""
        a = generate_shortcut_id('"a"', "GameA")
        b = generate_shortcut_id('"b"', "GameB")
        assert a != b

    def test_generate_preliminary_id_high_bit_set(self) -> None:
        """Preliminary ID always has bit 31 set in top 32 bits."""
        result = generate_preliminary_id('"test"', "Game")
        top32 = (result >> 32) & 0xFFFFFFFF
        assert top32 & 0x80000000 != 0

    def test_generate_preliminary_id_low_bits(self) -> None:
        """Low 32 bits of preliminary ID are always 0x02000000."""
        result = generate_preliminary_id('"test"', "Game")
        low32 = result & 0xFFFFFFFF
        assert low32 == 0x02000000

    def test_generate_app_id_is_string(self) -> None:
        """App ID for Big Picture is a string."""
        result = generate_app_id('"test"', "Game")
        assert isinstance(result, str)

    def test_generate_short_app_id_is_string(self) -> None:
        """Short App ID for grid images is a string."""
        result = generate_short_app_id('"test"', "Game")
        assert isinstance(result, str)

    def test_shortcut_id_roundtrip_via_vdf(self, tmp_path: Path) -> None:
        """Generated ID survives write → read cycle in VDF."""
        from src.core.shortcuts_manager import ShortcutsManager, SteamShortcut

        exe = '"/opt/Heroic/heroic"'
        name = "TestGame"
        expected_id = generate_shortcut_id(exe, name)

        userdata = tmp_path / "userdata"
        (userdata / "99" / "config").mkdir(parents=True)
        mgr = ShortcutsManager(userdata, "99")

        shortcut = SteamShortcut(appid=expected_id, app_name=name, exe=exe, start_dir='"."')
        mgr.write_shortcuts([shortcut])

        restored = mgr.read_shortcuts()
        assert restored[0].appid == expected_id

    def test_short_app_id_equals_preliminary_shifted(self) -> None:
        """Short App ID equals preliminary_id >> 32."""
        exe = '"test"'
        name = "Game"
        preliminary = generate_preliminary_id(exe, name)
        short = int(generate_short_app_id(exe, name))
        assert short == preliminary >> 32


# ---------------------------------------------------------------------------
# SteamShortcut dataclass
# ---------------------------------------------------------------------------


class TestSteamShortcut:
    """Tests for SteamShortcut data conversion."""

    def test_to_vdf_dict_keys(self) -> None:
        """to_vdf_dict produces correct key names."""
        s = SteamShortcut(
            appid=-100,
            app_name="Test",
            exe='"test"',
            start_dir='"."',
        )
        d = s.to_vdf_dict()
        assert d["appid"] == -100
        assert d["appname"] == "Test"
        assert d["exe"] == '"test"'
        assert d["StartDir"] == '"."'
        assert d["IsHidden"] == 0
        assert d["AllowDesktopConfig"] == 1
        assert d["tags"] == {}

    def test_from_vdf_dict_roundtrip(self) -> None:
        """from_vdf_dict reverses to_vdf_dict."""
        original = SteamShortcut(
            appid=-536285310,
            app_name="EmulationStationDE",
            exe='"/path/to/es-de.sh"',
            start_dir='"/home/user/"',
            icon='"/path/icon.ico"',
            tags={"0": "favorite"},
        )
        vdf = original.to_vdf_dict()
        restored = SteamShortcut.from_vdf_dict(vdf)
        assert restored.appid == original.appid
        assert restored.app_name == original.app_name
        assert restored.exe == original.exe
        assert restored.tags == original.tags

    def test_from_vdf_dict_missing_keys(self) -> None:
        """from_vdf_dict handles missing keys with defaults."""
        s = SteamShortcut.from_vdf_dict({"appid": -1, "appname": "X"})
        assert s.exe == ""
        assert s.start_dir == ""
        assert s.tags == {}
        assert s.allow_desktop_config is True

    def test_boolean_fields_from_int(self) -> None:
        """Boolean fields correctly convert from VDF int values."""
        s = SteamShortcut.from_vdf_dict(
            {
                "appid": -1,
                "appname": "Test",
                "IsHidden": 1,
                "AllowOverlay": 0,
            }
        )
        assert s.is_hidden is True
        assert s.allow_overlay is False


# ---------------------------------------------------------------------------
# ShortcutsManager
# ---------------------------------------------------------------------------


class TestShortcutsManager:
    """Tests for ShortcutsManager CRUD and backup."""

    def _make_manager(self, tmp_path: Path) -> ShortcutsManager:
        """Create a ShortcutsManager with temp paths."""
        userdata = tmp_path / "userdata"
        (userdata / "12345" / "config").mkdir(parents=True)
        return ShortcutsManager(userdata, "12345")

    def test_get_shortcuts_path(self, tmp_path: Path) -> None:
        """Shortcuts path follows Steam convention."""
        mgr = self._make_manager(tmp_path)
        expected = tmp_path / "userdata" / "12345" / "config" / "shortcuts.vdf"
        assert mgr.get_shortcuts_path() == expected

    def test_read_shortcuts_no_file(self, tmp_path: Path) -> None:
        """Returns empty list when shortcuts.vdf doesn't exist."""
        mgr = self._make_manager(tmp_path)
        assert mgr.read_shortcuts() == []

    def test_write_and_read_roundtrip(self, tmp_path: Path) -> None:
        """Written shortcuts can be read back."""
        mgr = self._make_manager(tmp_path)
        shortcuts = [
            SteamShortcut(
                appid=-100,
                app_name="Game A",
                exe='"game_a"',
                start_dir='"."',
            ),
            SteamShortcut(
                appid=-200,
                app_name="Game B",
                exe='"game_b"',
                start_dir='"."',
                tags={"0": "RPG"},
            ),
        ]
        mgr.write_shortcuts(shortcuts)
        result = mgr.read_shortcuts()
        assert len(result) == 2
        assert result[0].app_name == "Game A"
        assert result[1].app_name == "Game B"
        assert result[1].tags == {"0": "RPG"}

    def test_add_shortcut_creates_file(self, tmp_path: Path) -> None:
        """Adding a shortcut creates shortcuts.vdf if missing."""
        mgr = self._make_manager(tmp_path)
        s = SteamShortcut(appid=-100, app_name="New Game", exe='"new"', start_dir='"."')
        result = mgr.add_shortcut(s)
        assert result is True
        assert mgr.get_shortcuts_path().exists()
        assert len(mgr.read_shortcuts()) == 1

    def test_add_shortcut_duplicate_skipped(self, tmp_path: Path) -> None:
        """Duplicate shortcut by name is rejected."""
        mgr = self._make_manager(tmp_path)
        s = SteamShortcut(appid=-100, app_name="Existing", exe='"x"', start_dir='"."')
        mgr.add_shortcut(s)
        result = mgr.add_shortcut(s)
        assert result is False
        assert len(mgr.read_shortcuts()) == 1

    def test_add_shortcut_case_insensitive_duplicate(self, tmp_path: Path) -> None:
        """Duplicate detection is case-insensitive."""
        mgr = self._make_manager(tmp_path)
        s1 = SteamShortcut(appid=-100, app_name="Test Game", exe='"x"', start_dir='"."')
        s2 = SteamShortcut(appid=-200, app_name="test game", exe='"y"', start_dir='"."')
        mgr.add_shortcut(s1)
        assert mgr.add_shortcut(s2) is False

    def test_remove_shortcut(self, tmp_path: Path) -> None:
        """Remove deletes a shortcut by name."""
        mgr = self._make_manager(tmp_path)
        s = SteamShortcut(appid=-100, app_name="ToRemove", exe='"x"', start_dir='"."')
        mgr.add_shortcut(s)
        assert mgr.remove_shortcut("ToRemove") is True
        assert len(mgr.read_shortcuts()) == 0

    def test_remove_nonexistent_returns_false(self, tmp_path: Path) -> None:
        """Removing non-existent shortcut returns False."""
        mgr = self._make_manager(tmp_path)
        assert mgr.remove_shortcut("NoSuchGame") is False

    def test_has_shortcut(self, tmp_path: Path) -> None:
        """has_shortcut detects existing entries."""
        mgr = self._make_manager(tmp_path)
        s = SteamShortcut(appid=-100, app_name="Exists", exe='"x"', start_dir='"."')
        mgr.add_shortcut(s)
        assert mgr.has_shortcut("Exists") is True
        assert mgr.has_shortcut("exists") is True  # case-insensitive
        assert mgr.has_shortcut("Nope") is False

    def test_write_creates_backup(self, tmp_path: Path) -> None:
        """Writing creates a backup of the existing file."""
        mgr = self._make_manager(tmp_path)
        s = SteamShortcut(appid=-100, app_name="V1", exe='"x"', start_dir='"."')
        mgr.add_shortcut(s)
        # Write again to trigger backup
        s2 = SteamShortcut(appid=-200, app_name="V2", exe='"y"', start_dir='"."')
        mgr.add_shortcut(s2)
        backups = list(mgr.get_shortcuts_path().parent.glob("shortcuts.vdf.bak.*"))
        assert len(backups) >= 1

    def test_grid_paths(self, tmp_path: Path) -> None:
        """Grid paths follow Steam convention."""
        mgr = self._make_manager(tmp_path)
        paths = mgr.get_grid_paths('"test"', "Game")
        assert "cover" in paths
        assert "header" in paths
        assert "hero" in paths
        assert "logo" in paths
        assert "big_picture" in paths
        assert str(paths["cover"]).endswith("p.jpg")
        assert str(paths["logo"]).endswith("_logo.png")

    @pytest.mark.skipif(not _REAL_SHORTCUTS.exists(), reason="Real shortcuts.vdf not found")
    def test_read_real_shortcuts(self) -> None:
        """Read real shortcuts.vdf from the system."""
        userdata = _REAL_SHORTCUTS.parent.parent.parent
        mgr = ShortcutsManager(userdata, "43925226")
        shortcuts = mgr.read_shortcuts()
        assert len(shortcuts) == 13
        assert shortcuts[0].app_name == "EmulationStationDE"
        assert shortcuts[0].appid == -536285310
