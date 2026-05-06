#
# steam_library_manager/integrations/external_games/emulator_parsers/dolphin.py
# Dolphin (GameCube + Wii) emulator parser - INI config
#
# Copyright © 2025-2026 SwitchBros
# Licensed under the MIT License. See LICENSE for details.
#

from __future__ import annotations

import configparser
import logging
from pathlib import Path

from steam_library_manager.integrations.external_games.emulator_parsers._base import BaseEmulatorParser

__all__ = ["DolphinParser"]

logger = logging.getLogger("steamlibmgr.emulator_parsers.dolphin")


class DolphinParser(BaseEmulatorParser):
    """Dolphin - Nintendo GameCube + Wii emulator. Reads ISOPath0..N from Dolphin.ini."""

    EMULATOR_NAME = "Dolphin"
    EMULATOR_SYSTEMS = ("gc", "wii")
    FLATPAK_ID = "org.DolphinEmu.dolphin-emu"
    SYSTEM_BIN_NAMES = ("dolphin-emu", "dolphin-emu-nogui", "Dolphin", "dolphin", "Dolphin.AppImage")
    NATIVE_CONFIG_REL = ("dolphin-emu/Dolphin.ini",)
    FLATPAK_CONFIG_REL = ("dolphin-emu/Dolphin.ini",)

    def __init__(self, config_path: Path | None = None) -> None:
        self._config_override = config_path

    def iter_config_paths(self):
        if self._config_override is not None:
            yield self._config_override
            return
        yield from super().iter_config_paths()

    def _parse_config_file(self, path: Path) -> list[str]:
        # Dolphin.ini uses INI format with [General] section, ISOPaths = N count, ISOPathX rows
        cp = configparser.ConfigParser(strict=False, interpolation=None)
        try:
            cp.read(path, encoding="utf-8")
        except (configparser.Error, OSError) as exc:
            logger.warning("could not read %s: %s" % (path, exc))
            return []

        if not cp.has_section("General"):
            return []

        dirs: list[str] = []
        for key, value in cp.items("General"):
            if key.lower().startswith("isopath") and key.lower() != "isopaths":
                v = value.strip()
                if v:
                    dirs.append(v)
        return dirs
