# src/utils/appinfo_constants.py

"""Constants for the Steam AppInfo.vdf binary format.

Extracted from appinfo.py to separate constants/enums from parser logic.
Contains version definitions, binary VDF type markers, enums, and error types.
"""

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


# ===== VERSION DEFINITIONS =====


class AppInfoVersion(IntEnum):
    """AppInfo format version identifiers.

    These are the magic numbers used to identify different versions of the
    appinfo.vdf file format.
    """

    # Old versions (for reference, not implemented)
    # VERSION_24 = 0x06445624  # circa 2011
    # VERSION_25 = 0x07445625  # circa 2012
    # VERSION_26 = 0x07445626  # circa 2013
    # VERSION_27 = 0x07445627  # circa 2017

    # Supported versions
    VERSION_28 = 0x07564428  # Dec 2022 - June 2024 (Binary SHA-1)
    VERSION_29 = 0x07564429  # June 2024+ (String Table)
    VERSION_39 = 0x07564427  # Alternate magic for v27
    VERSION_40 = 0x07564428  # Alternate magic for v28
    VERSION_41 = 0x07564429  # Alternate magic for v29


class EUniverse(IntEnum):
    """Steam Universe identifiers.

    Defines the Steam environment the appinfo.vdf file belongs to.
    """

    Invalid = 0
    Public = 1
    Beta = 2
    Internal = 3
    Dev = 4


# ===== MAGIC NUMBERS & VALID VERSIONS =====

MAGIC_NUMBER: int = 0x07_56_44
"""Expected magic prefix in the appinfo.vdf header (3 bytes, shifted)."""

VALID_VERSIONS: tuple[int, ...] = (28, 29, 39, 40, 41)
"""Supported appinfo.vdf version numbers."""


# ===== BINARY VDF TYPE MARKERS =====

TYPE_DICT: int = 0x00
TYPE_STRING: int = 0x01
TYPE_INT32: int = 0x02
TYPE_FLOAT32: int = 0x03
TYPE_POINTER: int = 0x04  # Unused
TYPE_WIDESTRING: int = 0x05  # Unused
TYPE_COLOR: int = 0x06  # Unused
TYPE_INT64: int = 0x07
TYPE_SECTION_END: int = 0x08
TYPE_END: int = 0x08  # Alias for TYPE_SECTION_END


# ===== EXCEPTIONS =====


class IncompatibleVersionError(Exception):
    """Raised when an unsupported appinfo.vdf version is encountered.

    Attributes:
        version: The version number that was detected.
        magic: The magic number that was read from the file.
    """

    def __init__(self, version: int, magic: int):
        """Initializes the exception.

        Args:
            version: The version number that was detected.
            magic: The magic number that was read from the file.
        """
        self.version = version
        self.magic = magic
        super().__init__(f"Incompatible version {version} (magic: 0x{magic:08X})")
