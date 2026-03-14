#
# steam_library_manager/utils/appinfo.py
# Steam AppInfo.vdf parser with full read and write support
#
# Copyright © 2025-2026 SwitchBros
# Licensed under the MIT License. See LICENSE for details.
#

from __future__ import annotations

import hashlib
import logging
import struct
from typing import BinaryIO

# Import i18n if available (optional for standalone use)
try:
    from steam_library_manager.utils.i18n import t

    HAS_I18N = True
except ImportError:
    HAS_I18N = False

    def t(key: str, **_kwargs: object) -> str:
        """Fallback translation function for standalone use."""
        return key.split(".")[-1]


from steam_library_manager.utils.appinfo_constants import (
    EUniverse,
    IncompatibleVersionError,
    MAGIC_NUMBER,
    TYPE_DICT,
    TYPE_FLOAT32,
    TYPE_INT32,
    TYPE_INT64,
    TYPE_SECTION_END,
    TYPE_STRING,
    VALID_VERSIONS,
)

__all__ = ("AppInfo", "IncompatibleVersionError", "load", "loads")

logger = logging.getLogger("steamlibmgr.appinfo")


# Main parser class


class AppInfo:
    """Parser for Steam's appinfo.vdf file format.

    Supports versions 28, 29, 39, 40, and 41 with correct checksum
    calculation and string table handling.
    """

    def __init__(self, path: str | None = None, data: bytes | None = None):
        self.file_path = path
        self.data = None
        self.offset = 0

        # Parsed data
        self.magic = 0
        self.version = 0
        self.universe = EUniverse.Public
        self.apps: dict[int, dict] = {}

        # Version-specific
        self.string_table: list[str] = []
        self.string_table_offset = 0

        # Load data
        if path:
            with open(path, "rb") as f:
                self.data = bytearray(f.read())
        elif data:
            self.data = bytearray(data)
        else:
            raise ValueError(t("errors.appinfo.no_data"))

        # Parse header
        self._parse_header()

        # Parse apps
        self._parse_apps()

    # Header parsing

    def _parse_header(self):
        """Parses the file header and detects the version."""
        # Read magic (4 bytes)
        raw_magic = self._read_uint32()

        # Extract version from magic
        self.version = raw_magic & 0xFF
        self.magic = raw_magic >> 8

        # Verify magic number
        if self.magic != MAGIC_NUMBER:
            raise IncompatibleVersionError(self.version, raw_magic)

        # Verify version
        if self.version not in VALID_VERSIONS:
            raise IncompatibleVersionError(self.version, raw_magic)

        # Read universe
        self.universe = EUniverse(self._read_uint32())

        # Version 41+ has string table offset
        if self.version >= 41:
            self.string_table_offset = self._read_int64()
            # Parse string table
            self._parse_string_table()

    def _parse_string_table(self):
        """Parses the string table for version 41+ files."""
        # Save current position
        saved_offset = self.offset

        # Jump to string table
        self.offset = self.string_table_offset

        # Read string count
        string_count = self._read_uint32()

        # Read strings
        self.string_table = []
        for _ in range(string_count):
            string = self._read_cstring()
            self.string_table.append(string)

        # Restore position
        self.offset = saved_offset

    # App parsing

    def _parse_apps(self):
        """Parses all app entries from the file."""
        while True:
            # Read app ID
            current_app_id = self._read_uint32()

            # Check for end marker
            if current_app_id == 0:
                break

            # Parse app entry
            try:
                current_app_data = self._parse_app_entry()
                self.apps[current_app_id] = current_app_data
            except Exception as e:
                logger.warning(t("logs.appinfo.parse_error", app_id=current_app_id, error=e))
                continue

    def _parse_app_entry(self) -> dict:
        """Parses a single app entry."""
        app_entry = {}

        # Version-specific parsing
        if self.version >= 36:
            # Read size field
            app_entry["size"] = self._read_uint32()

        # Read info state
        app_entry["info_state"] = self._read_uint32()

        # Read last updated
        app_entry["last_updated"] = self._read_uint32()

        # Version 38+ has access token
        if self.version >= 38:
            app_entry["access_token"] = self._read_uint64()

        # Version 38+ has SHA-1 hash
        if self.version >= 38:
            app_entry["sha1_hash"] = self.data[self.offset : self.offset + 20]
            self.offset += 20

        # Version 36+ has change number
        if self.version >= 36:
            app_entry["change_number"] = self._read_uint32()

        # Version 40+ has binary SHA-1 hash
        if self.version >= 40:
            app_entry["binary_sha1"] = self.data[self.offset : self.offset + 20]
            self.offset += 20

        # Parse binary VDF data
        app_entry["data"] = self._parse_vdf()

        return app_entry

    # VDF parsing

    def _parse_vdf(self) -> dict:
        """Parses binary VDF (Key-Value) data."""
        result = {}

        while True:
            # Read value type
            value_type = self._read_byte()

            # Check for end marker
            if value_type == TYPE_SECTION_END:
                break

            # Read key
            key = self._read_key()

            # Parse value based on type
            if value_type == TYPE_DICT:
                # Nested dictionary
                result[key] = self._parse_vdf()

            elif value_type == TYPE_STRING:
                # String value
                result[key] = self._read_cstring()

            elif value_type == TYPE_INT32:
                # 32-bit integer
                result[key] = self._read_int32()

            elif value_type == TYPE_FLOAT32:
                # 32-bit float
                result[key] = self._read_float32()

            elif value_type == TYPE_INT64:
                # 64-bit integer
                result[key] = self._read_int64()

            else:
                # Unknown type - skip
                logger.warning(t("logs.appinfo.unknown_vdf_type", type=f"0x{value_type:02x}"))
                break

        return result

    # Read primitives

    def _read_byte(self) -> int:
        """Reads a single byte from the data."""
        value = self.data[self.offset]
        self.offset += 1
        return value

    def _read_int32(self) -> int:
        """Reads a signed 32-bit integer."""
        value = struct.unpack_from("<i", self.data, self.offset)[0]
        self.offset += 4
        return value

    def _read_uint32(self) -> int:
        """Reads an unsigned 32-bit integer."""
        value = struct.unpack_from("<I", self.data, self.offset)[0]
        self.offset += 4
        return value

    def _read_int64(self) -> int:
        """Reads a signed 64-bit integer."""
        value = struct.unpack_from("<q", self.data, self.offset)[0]
        self.offset += 8
        return value

    def _read_uint64(self) -> int:
        """Reads an unsigned 64-bit integer."""
        value = struct.unpack_from("<Q", self.data, self.offset)[0]
        self.offset += 8
        return value

    def _read_float32(self) -> float:
        """Reads a 32-bit float."""
        value = struct.unpack_from("<f", self.data, self.offset)[0]
        self.offset += 4
        return value

    def _read_cstring(self) -> str:
        """Reads a null-terminated string (UTF-8 with latin-1 fallback)."""
        end = self.data.find(0, self.offset)
        if end == -1:
            end = len(self.data)

        string_bytes = self.data[self.offset : end]
        self.offset = end + 1

        # Try UTF-8 first, fallback to latin-1
        try:
            return string_bytes.decode("utf-8")
        except UnicodeDecodeError:
            return string_bytes.decode("latin-1", errors="replace")

    def _read_key(self) -> str:
        """Reads a key - string table index for v41+, direct string otherwise."""
        if self.version >= 41 and self.string_table:
            # Read string table index
            index = self._read_uint32()

            # Bounds check
            if index >= len(self.string_table):
                logger.warning(t("logs.appinfo.string_index_warning", index=index, size=len(self.string_table)))
                return f"__unknown_{index}__"

            return self.string_table[index]
        else:
            # Direct string
            return self._read_cstring()

    # Write support

    def write(self, output_path: str | None = None) -> bool:
        """Writes the appinfo.vdf back to disk with correct checksums."""
        if output_path is None:
            if self.file_path is None:
                raise ValueError(t("errors.appinfo.no_output_path"))
            output_path = self.file_path

        try:
            # Build new file data
            output = bytearray()

            # Write header
            self._write_header(output)

            # Write apps
            self._write_apps(output)

            # Write footer (app_id = 0)
            output.extend(struct.pack("<I", 0))

            # Update string table (v41+)
            if self.version >= 41:
                self._write_string_table(output)

            # Write to file
            with open(output_path, "wb") as f:
                f.write(output)

            return True

        except Exception as e:
            logger.error(t("logs.appinfo.write_error", error=str(e)))
            logger.debug(t("logs.appinfo.write_error_detail", error=e), exc_info=True)
            return False

    def _write_header(self, output: bytearray):
        """Writes the file header."""
        # Write magic + version
        magic_version = (self.magic << 8) | self.version
        output.extend(struct.pack("<I", magic_version))

        # Write universe
        output.extend(struct.pack("<I", self.universe))

        # Version 41+ has string table offset (placeholder)
        if self.version >= 41:
            # Will be updated later
            output.extend(struct.pack("<Q", 0))

    def _write_apps(self, output: bytearray):
        """Writes all app entries."""
        for current_app_id, current_app_data in self.apps.items():
            self._write_app_entry(output, current_app_id, current_app_data)

    def _write_app_entry(self, output: bytearray, entry_app_id: int, entry_app_data: dict):
        """Writes a single app entry."""
        # Write app ID
        output.extend(struct.pack("<I", entry_app_id))

        # Encode VDF data
        vdf_data = self._encode_vdf(entry_app_data.get("data", {}))

        # Calculate size (if needed)
        if self.version >= 36:
            # Size = everything after size field
            size = (
                4  # info_state
                + 4  # last_updated
                + (8 if self.version >= 38 else 0)  # access_token
                + (20 if self.version >= 38 else 0)  # sha1_hash
                + (4 if self.version >= 36 else 0)  # change_number
                + (20 if self.version >= 40 else 0)  # binary_sha1
                + len(vdf_data)
            )
            output.extend(struct.pack("<I", size))

        # Write info state
        output.extend(struct.pack("<I", entry_app_data.get("info_state", 2)))

        # Write last updated
        output.extend(struct.pack("<I", entry_app_data.get("last_updated", 0)))

        # Version 38+ has access token
        if self.version >= 38:
            output.extend(struct.pack("<Q", entry_app_data.get("access_token", 0)))

        # Version 38+ has SHA-1 hash
        if self.version >= 38:
            # Calculate text VDF SHA-1
            text_vdf = self._dict_to_text_vdf(entry_app_data.get("data", {}))
            sha1_hash = hashlib.sha1(text_vdf).digest()
            output.extend(sha1_hash)

        # Version 36+ has change number
        if self.version >= 36:
            output.extend(struct.pack("<I", entry_app_data.get("change_number", 0)))

        # Version 40+ has binary SHA-1 hash
        if self.version >= 40:
            binary_sha1 = hashlib.sha1(vdf_data).digest()
            output.extend(binary_sha1)

        # Write VDF data
        output.extend(vdf_data)

    def _encode_vdf(self, vdf_data: dict) -> bytearray:
        """Encodes a dictionary to binary VDF format."""
        output = bytearray()

        for key, value in vdf_data.items():
            if isinstance(value, dict):
                # Nested dictionary
                output.append(TYPE_DICT)
                output.extend(self._encode_key(key))
                output.extend(self._encode_vdf(value))

            elif isinstance(value, str):
                # String value
                output.append(TYPE_STRING)
                output.extend(self._encode_key(key))
                output.extend(self._encode_cstring(value))

            elif isinstance(value, float):
                # Float value
                output.append(TYPE_FLOAT32)
                output.extend(self._encode_key(key))
                output.extend(struct.pack("<f", value))

            elif isinstance(value, int):
                # Integer value - check range
                if -2147483648 <= value <= 2147483647:
                    # 32-bit
                    output.append(TYPE_INT32)
                    output.extend(self._encode_key(key))
                    output.extend(struct.pack("<i", value))
                else:
                    # 64-bit
                    output.append(TYPE_INT64)
                    output.extend(self._encode_key(key))
                    output.extend(struct.pack("<q", value))

        # End marker
        output.append(TYPE_SECTION_END)

        return output

    def _encode_key(self, key: str) -> bytearray:
        """Encodes a key - string table index for v41+, direct string otherwise."""
        if self.version >= 41 and self.string_table:
            # Find or add to string table
            try:
                index = self.string_table.index(key)
            except ValueError:
                # Add new string
                index = len(self.string_table)
                self.string_table.append(key)

            return bytearray(struct.pack("<I", index))
        else:
            # Direct string
            return self._encode_cstring(key)

    @staticmethod
    def _encode_cstring(string: str) -> bytearray:
        """Encodes a null-terminated string."""
        try:
            return bytearray(string.encode("utf-8") + b"\x00")
        except UnicodeEncodeError:
            return bytearray(string.encode("latin-1", errors="replace") + b"\x00")

    def _write_string_table(self, output: bytearray):
        """Writes the string table and updates the offset in the header."""
        # Record string table position
        string_table_offset = len(output)

        # Write string count
        output.extend(struct.pack("<I", len(self.string_table)))

        # Write strings
        for string in self.string_table:
            output.extend(self._encode_cstring(string))

        # Update offset in header (byte 8-15)
        struct.pack_into("<Q", output, 8, string_table_offset)

    def _dict_to_text_vdf(self, vdf_dict: dict, indent: int = 0) -> bytes:
        """Converts a dictionary to text VDF format for SHA-1 calculation."""
        output = b""
        tabs = b"\t" * indent

        for key, value in vdf_dict.items():
            # Escape backslashes in key
            key_escaped = key.replace("\\", "\\\\")

            if isinstance(value, dict):
                # Nested dict
                output += tabs + b'"' + key_escaped.encode("utf-8", errors="replace") + b'"\n'
                output += tabs + b"{\n"
                output += self._dict_to_text_vdf(value, indent + 1)
                output += tabs + b"}\n"
            else:
                # Value
                value_str = str(value).replace("\\", "\\\\")
                output += (
                    tabs
                    + b'"'
                    + key_escaped.encode("utf-8", errors="replace")
                    + b'"\t\t"'
                    + value_str.encode("utf-8", errors="replace")
                    + b'"\n'
                )

        return output

    # Convenience methods

    def get_app(self, app_id: int) -> dict | None:
        return self.apps.get(app_id)

    def set_app(self, set_app_id: int, set_data: dict):
        """Sets app data for a specific app ID, creating the entry if needed."""
        if set_app_id not in self.apps:
            self.apps[set_app_id] = {"info_state": 2, "last_updated": 0, "data": {}}

        self.apps[set_app_id]["data"] = set_data

    def update_app_metadata(self, update_app_id: int, metadata: dict):
        """Updates app metadata in the 'common' section."""
        if update_app_id not in self.apps:
            return False

        app_data_dict = self.apps[update_app_id].get("data", {})

        if "common" not in app_data_dict:
            app_data_dict["common"] = {}

        common_section = app_data_dict["common"]

        # Update fields
        if "name" in metadata:
            common_section["name"] = metadata["name"]
        if "developer" in metadata:
            common_section["developer"] = metadata["developer"]
        if "publisher" in metadata:
            common_section["publisher"] = metadata["publisher"]
        if "release_date" in metadata:
            common_section["steam_release_date"] = metadata["release_date"]

        return True

    def __len__(self) -> int:
        """Returns the number of apps."""
        return len(self.apps)

    def __contains__(self, check_app_id: int) -> bool:
        return check_app_id in self.apps

    def __getitem__(self, get_app_id: int) -> dict:
        return self.apps[get_app_id]

    def __repr__(self) -> str:
        return f"<AppInfo v{self.version} with {len(self.apps)} apps>"


# Simple API


def load(fp: BinaryIO) -> AppInfo:
    """Loads appinfo.vdf from a file object."""
    return AppInfo(data=fp.read())


def loads(file_data: bytes) -> AppInfo:
    """Loads appinfo.vdf from bytes."""
    return AppInfo(data=file_data)
