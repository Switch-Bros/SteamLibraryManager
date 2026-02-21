"""Tests for binary VDF parser.

Covers read, write, roundtrip, and edge cases for
Steam shortcuts.vdf binary format.
"""

from __future__ import annotations

import struct
from io import BytesIO
from pathlib import Path

import pytest

from src.core.vdf_parser import (
    BIN_END,
    BIN_INT32,
    BIN_NONE,
    BIN_STRING,
    binary_dump,
    binary_dumps,
    binary_load,
    binary_loads,
)

# Path to the real shortcuts.vdf on the system
_REAL_SHORTCUTS = Path.home() / ".local" / "share" / "Steam" / "userdata" / "43925226" / "config" / "shortcuts.vdf"


class TestBinaryLoads:
    """Tests for binary_loads (bytes → dict)."""

    def test_empty_shortcuts(self) -> None:
        """Empty shortcuts.vdf with just header and end markers."""
        data = b"\x00shortcuts\x00\x08\x08"
        result = binary_loads(data)
        assert result == {"shortcuts": {}}

    def test_single_shortcut(self) -> None:
        """Single shortcut entry with appid and appname."""
        buf = BytesIO()
        # Root → shortcuts dict
        buf.write(BIN_NONE + b"shortcuts\x00")
        # Entry "0"
        buf.write(BIN_NONE + b"0\x00")
        buf.write(BIN_INT32 + b"appid\x00" + struct.pack("<i", -536285310))
        buf.write(BIN_STRING + b"appname\x00" + b"TestGame\x00")
        buf.write(BIN_END)  # end entry
        buf.write(BIN_END)  # end shortcuts
        buf.write(BIN_END)  # end root

        result = binary_loads(buf.getvalue())
        shortcuts = result["shortcuts"]
        assert isinstance(shortcuts, dict)
        assert "0" in shortcuts
        assert shortcuts["0"]["appid"] == -536285310
        assert shortcuts["0"]["appname"] == "TestGame"

    def test_nested_tags_dict(self) -> None:
        """Tags stored as nested dict with string indices."""
        buf = BytesIO()
        buf.write(BIN_NONE + b"shortcuts\x00")
        buf.write(BIN_NONE + b"0\x00")
        buf.write(BIN_INT32 + b"appid\x00" + struct.pack("<i", -100))
        buf.write(BIN_STRING + b"appname\x00" + b"Game\x00")
        # Tags
        buf.write(BIN_NONE + b"tags\x00")
        buf.write(BIN_STRING + b"0\x00" + b"favorite\x00")
        buf.write(BIN_STRING + b"1\x00" + b"Emulation\x00")
        buf.write(BIN_END)  # end tags
        buf.write(BIN_END)  # end entry
        buf.write(BIN_END)  # end shortcuts
        buf.write(BIN_END)  # end root

        result = binary_loads(buf.getvalue())
        tags = result["shortcuts"]["0"]["tags"]
        assert tags == {"0": "favorite", "1": "Emulation"}

    def test_empty_bytes_returns_empty_dict(self) -> None:
        """Empty input returns empty dict."""
        assert binary_loads(b"") == {}

    def test_negative_appid_preserved(self) -> None:
        """Negative signed int32 appid values are correctly preserved."""
        known_ids = [-536285310, -150539546, -1142811861, -431680008]
        for expected_id in known_ids:
            buf = BytesIO()
            buf.write(BIN_NONE + b"s\x00")
            buf.write(BIN_NONE + b"0\x00")
            buf.write(BIN_INT32 + b"appid\x00" + struct.pack("<i", expected_id))
            buf.write(BIN_END + BIN_END + BIN_END)
            result = binary_loads(buf.getvalue())
            assert result["s"]["0"]["appid"] == expected_id

    def test_quoted_exe_paths(self) -> None:
        """Double-quoted exe paths are preserved as-is."""
        exe = '"/opt/Heroic/heroic"'
        buf = BytesIO()
        buf.write(BIN_NONE + b"s\x00")
        buf.write(BIN_NONE + b"0\x00")
        buf.write(BIN_STRING + b"exe\x00" + exe.encode("utf-8") + b"\x00")
        buf.write(BIN_END + BIN_END + BIN_END)
        result = binary_loads(buf.getvalue())
        assert result["s"]["0"]["exe"] == exe


class TestBinaryDumps:
    """Tests for binary_dumps (dict → bytes)."""

    def test_empty_shortcuts_roundtrip(self) -> None:
        """Empty shortcuts dict produces correct binary."""
        data = binary_dumps({"shortcuts": {}})
        assert data == b"\x00shortcuts\x00\x08\x08"

    def test_string_value(self) -> None:
        """String values are encoded with BIN_STRING tag."""
        data = binary_dumps({"root": {"key": "value"}})
        result = binary_loads(data)
        assert result["root"]["key"] == "value"

    def test_int32_value(self) -> None:
        """Int32 values within range use BIN_INT32."""
        data = binary_dumps({"root": {"n": -536285310}})
        # Verify BIN_INT32 tag is used (not INT64)
        assert b"\x02n\x00" in data
        result = binary_loads(data)
        assert result["root"]["n"] == -536285310

    def test_float_value(self) -> None:
        """Float values use BIN_FLOAT32."""
        data = binary_dumps({"root": {"f": 3.14}})
        result = binary_loads(data)
        assert abs(result["root"]["f"] - 3.14) < 0.01

    def test_large_int_uses_int64(self) -> None:
        """Values exceeding int32 range use BIN_INT64."""
        large = 2**31  # Just over int32 max
        data = binary_dumps({"root": {"big": large}})
        result = binary_loads(data)
        assert result["root"]["big"] == large

    def test_dict_ordering_preserved(self) -> None:
        """Key insertion order is preserved in output."""
        obj = {"shortcuts": {"0": {"appid": -1, "appname": "A", "exe": "x"}}}
        data = binary_dumps(obj)
        result = binary_loads(data)
        keys = list(result["shortcuts"]["0"].keys())
        assert keys == ["appid", "appname", "exe"]


class TestBinaryRoundtrip:
    """Tests for load → dump → load consistency."""

    def test_simple_roundtrip(self) -> None:
        """Simple dict survives roundtrip."""
        original = {
            "shortcuts": {
                "0": {
                    "appid": -100,
                    "appname": "Test",
                    "exe": '"test"',
                    "StartDir": "./",
                    "tags": {"0": "favorite"},
                },
            },
        }
        data = binary_dumps(original)
        result = binary_loads(data)
        assert result == original

    def test_multiple_entries_roundtrip(self) -> None:
        """Multiple shortcut entries survive roundtrip."""
        original = {
            "shortcuts": {
                "0": {"appid": -100, "appname": "Game A", "exe": '"a"'},
                "1": {"appid": -200, "appname": "Game B", "exe": '"b"'},
                "2": {"appid": -300, "appname": "Game C", "exe": '"c"'},
            },
        }
        data = binary_dumps(original)
        result = binary_loads(data)
        assert len(result["shortcuts"]) == 3
        assert result == original

    @pytest.mark.skipif(not _REAL_SHORTCUTS.exists(), reason="Real shortcuts.vdf not found")
    def test_real_file_roundtrip(self) -> None:
        """Real shortcuts.vdf survives byte-for-byte roundtrip."""
        raw = _REAL_SHORTCUTS.read_bytes()
        parsed = binary_loads(raw)
        rewritten = binary_dumps(parsed)
        assert raw == rewritten

    @pytest.mark.skipif(not _REAL_SHORTCUTS.exists(), reason="Real shortcuts.vdf not found")
    def test_real_file_13_entries(self) -> None:
        """Real shortcuts.vdf contains expected 13 entries."""
        raw = _REAL_SHORTCUTS.read_bytes()
        parsed = binary_loads(raw)
        shortcuts = parsed.get("shortcuts", {})
        assert len(shortcuts) == 13

    @pytest.mark.skipif(not _REAL_SHORTCUTS.exists(), reason="Real shortcuts.vdf not found")
    def test_real_file_known_entry(self) -> None:
        """Real file contains EmulationStationDE with known appid."""
        raw = _REAL_SHORTCUTS.read_bytes()
        parsed = binary_loads(raw)
        entry = parsed["shortcuts"]["0"]
        assert entry["appname"] == "EmulationStationDE"
        assert entry["appid"] == -536285310
        assert entry["tags"] == {"0": "favorite"}


class TestBinaryLoadDump:
    """Tests for file-like object API (binary_load/binary_dump)."""

    def test_load_from_stream(self) -> None:
        """binary_load reads from file-like object."""
        data = binary_dumps({"test": {"key": "val"}})
        result = binary_load(BytesIO(data))
        assert result["test"]["key"] == "val"

    def test_dump_to_stream(self) -> None:
        """binary_dump writes to file-like object."""
        obj = {"test": {"key": "val"}}
        buf = BytesIO()
        binary_dump(obj, buf)
        buf.seek(0)
        result = binary_load(buf)
        assert result == obj
