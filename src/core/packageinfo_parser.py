# src/core/packageinfo_parser.py

"""Parser for Steam's binary packageinfo.vdf file.

Steam stores license/package data in ``appcache/packageinfo.vdf``.
Each package grants access to one or more app IDs.  Parsing this file
gives us the **definitive list of all owned app IDs** — including games
that the Steam Web API's ``GetOwnedGames`` endpoint does not return.
"""

from __future__ import annotations

import logging
import struct
from pathlib import Path

from src.utils.i18n import t

logger = logging.getLogger("steamlibmgr.packageinfo")

__all__ = ["PackageInfoParser"]


class PackageInfoParser:
    """Extracts owned app IDs from Steam's binary packageinfo.vdf."""

    def __init__(self, steam_path: Path) -> None:
        """Initializes the parser.

        Args:
            steam_path: Path to the Steam installation directory.
        """
        self._path = steam_path / "appcache" / "packageinfo.vdf"

    def get_all_app_ids(self) -> set[str]:
        """Parses packageinfo.vdf and returns all app IDs from all packages.

        Returns:
            Set of app ID strings found across all packages.
        """
        if not self._path.exists():
            logger.warning(t("logs.manager.packageinfo_not_found"))
            return set()

        app_ids: set[str] = set()

        try:
            with open(self._path, "rb") as f:
                # Header: version (4 bytes) + universe (4 bytes)
                f.read(8)

                while True:
                    pkg_id_bytes = f.read(4)
                    if len(pkg_id_bytes) < 4:
                        break
                    pkg_id = struct.unpack("<I", pkg_id_bytes)[0]

                    # End-of-file marker
                    if pkg_id == 0xFFFFFFFF:
                        break

                    # SHA1 hash (20) + change number (4) + token (8)
                    f.read(32)

                    data = self._read_binary_vdf(f)

                    # Package data is wrapped in one outer key
                    inner = next(iter(data.values()), data) if data else {}
                    for val in inner.get("appids", {}).values():
                        app_ids.add(str(val))

        except (OSError, struct.error) as exc:
            logger.error("packageinfo.vdf parse error: %s", exc)

        return app_ids

    # ------------------------------------------------------------------
    # Binary VDF reader (minimal, read-only)
    # ------------------------------------------------------------------

    @staticmethod
    def _read_binary_vdf(f, depth: int = 0, max_depth: int = 5) -> dict:
        """Reads a single binary VDF object from the file stream.

        Args:
            f: Open binary file handle positioned at the start of an object.
            depth: Current nesting depth (for recursion guard).
            max_depth: Maximum allowed nesting depth.

        Returns:
            Parsed dictionary of key-value pairs.
        """
        result: dict = {}
        while True:
            type_byte = f.read(1)
            if not type_byte or type_byte == b"\x08":
                break

            vdf_type = type_byte[0]

            # Read null-terminated key name
            key_parts: list[bytes] = []
            while True:
                c = f.read(1)
                if not c or c == b"\x00":
                    break
                key_parts.append(c)
            key_str = b"".join(key_parts).decode("utf-8", errors="replace")

            if vdf_type == 0x00:  # sub-object
                if depth < max_depth:
                    result[key_str] = PackageInfoParser._read_binary_vdf(f, depth + 1, max_depth)
                else:
                    result[key_str] = {}
            elif vdf_type == 0x01:  # string
                val_parts: list[bytes] = []
                while True:
                    c = f.read(1)
                    if not c or c == b"\x00":
                        break
                    val_parts.append(c)
                result[key_str] = b"".join(val_parts).decode("utf-8", errors="replace")
            elif vdf_type == 0x02:  # uint32
                result[key_str] = struct.unpack("<I", f.read(4))[0]
            elif vdf_type == 0x07:  # uint64
                result[key_str] = struct.unpack("<Q", f.read(8))[0]
            else:
                break

        return result
