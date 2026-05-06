#
# steam_library_manager/integrations/external_games/emulator_parsers/ppsspp.py
# PPSSPP (PSP) emulator parser - INI config with RecentISOs
#
# Copyright © 2025-2026 SwitchBros
# Licensed under the MIT License. See LICENSE for details.
#

from __future__ import annotations

import configparser
import logging
from pathlib import Path

from steam_library_manager.integrations.external_games.emulator_parsers._base import BaseEmulatorParser

__all__ = ["PPSSPPParser"]

logger = logging.getLogger("steamlibmgr.emulator_parsers.ppsspp")


class PPSSPPParser(BaseEmulatorParser):
    """PPSSPP - PlayStation Portable emulator. Reads RecentISOs as a hint."""

    EMULATOR_NAME = "PPSSPP"
    EMULATOR_SYSTEMS = ("psp",)
    FLATPAK_ID = "org.ppsspp.PPSSPP"
    SYSTEM_BIN_NAMES = ("PPSSPPSDL", "ppsspp", "PPSSPP", "PPSSPP.AppImage")
    NATIVE_CONFIG_REL = ("ppsspp/PSP/SYSTEM/ppsspp.ini",)
    FLATPAK_CONFIG_REL = ("ppsspp/PSP/SYSTEM/ppsspp.ini",)

    def __init__(self, config_path: Path | None = None) -> None:
        self._config_override = config_path

    def iter_config_paths(self):
        if self._config_override is not None:
            yield self._config_override
            return
        yield from super().iter_config_paths()

    def _parse_config_file(self, path: Path) -> list[str]:
        # PPSSPP stores recently opened files; we extract their parent dirs as a hint
        cp = configparser.ConfigParser(strict=False, interpolation=None)
        try:
            cp.read(path, encoding="utf-8")
        except (configparser.Error, OSError) as exc:
            logger.warning("could not read %s: %s" % (path, exc))
            return []

        section = None
        for s in cp.sections():
            if "Recent" in s:
                section = s
                break
        if not section:
            return []

        seen: set[str] = set()
        for _, value in cp.items(section):
            v = value.strip().strip('"')
            if not v:
                continue
            parent = str(Path(v).parent)
            if parent and parent != "." and parent not in seen:
                seen.add(parent)
        return sorted(seen)
