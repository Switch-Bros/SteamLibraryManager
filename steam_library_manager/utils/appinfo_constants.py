#
# steam_library_manager/utils/appinfo_constants.py
# Constants for Steam appinfo.vdf binary format
#
# Copyright © 2025-2026 SwitchBros
# Licensed under the MIT License. See LICENSE for details.
#

from __future__ import annotations

from enum import IntEnum

__all__ = [
    "AppInfoVersion",
    "EUniverse",
    "IncompatibleVersionError",
    "MAGIC_NUMBER",
    "TYPE_COLOR",
    "TYPE_DICT",
    "TYPE_END",
    "TYPE_FLOAT32",
    "TYPE_INT32",
    "TYPE_INT64",
    "TYPE_POINTER",
    "TYPE_SECTION_END",
    "TYPE_STRING",
    "TYPE_WIDESTRING",
    "VALID_VERSIONS",
]


class AppInfoVersion(IntEnum):
    # supported appinfo.vdf versions
    VERSION_28 = 0x07564428  # dec 2022 - june 2024
    VERSION_29 = 0x07564429  # june 2024+
    VERSION_39 = 0x07564427
    VERSION_40 = 0x07564428
    VERSION_41 = 0x07564429


class EUniverse(IntEnum):
    Invalid = 0
    Public = 1
    Beta = 2
    Internal = 3
    Dev = 4


# header magic (3 bytes shifted)
MAGIC_NUMBER = 0x07_56_44

VALID_VERSIONS = (28, 29, 39, 40, 41)

# binary vdf type markers
TYPE_DICT = 0x00
TYPE_STRING = 0x01
TYPE_INT32 = 0x02
TYPE_FLOAT32 = 0x03
TYPE_POINTER = 0x04
TYPE_WIDESTRING = 0x05
TYPE_COLOR = 0x06
TYPE_INT64 = 0x07
TYPE_SECTION_END = 0x08
TYPE_END = 0x08


class IncompatibleVersionError(Exception):
    def __init__(self, ver, magic):
        self.version = ver
        self.magic = magic
        super().__init__("Incompatible version %d (magic: 0x%08X)" % (ver, magic))
