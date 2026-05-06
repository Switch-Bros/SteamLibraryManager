#
# steam_library_manager/integrations/external_games/emulator_parsers/ryujinx.py
# Ryujinx (Switch) emulator parser - JSON config
#
# Copyright © 2025-2026 SwitchBros
# Licensed under the MIT License. See LICENSE for details.
#

from __future__ import annotations

import json
import logging
from pathlib import Path

from steam_library_manager.integrations.external_games.emulator_parsers._base import BaseEmulatorParser

__all__ = ["RyujinxParser"]

logger = logging.getLogger("steamlibmgr.emulator_parsers.ryujinx")


class RyujinxParser(BaseEmulatorParser):
    """Ryujinx - Nintendo Switch emulator. Reads game_dirs from Config.json."""

    EMULATOR_NAME = "Ryujinx"
    EMULATOR_SYSTEMS = ("switch",)
    FLATPAK_ID = "org.ryujinx.Ryujinx"
    SYSTEM_BIN_NAMES = ("Ryujinx", "ryujinx", "Ryujinx.sh", "Ryujinx.AppImage")
    NATIVE_CONFIG_REL = ("Ryujinx/Config.json",)
    FLATPAK_CONFIG_REL = ("Ryujinx/Config.json",)

    def __init__(self, config_path: Path | None = None) -> None:
        self._config_override = config_path

    def iter_config_paths(self):
        if self._config_override is not None:
            yield self._config_override
            return
        yield from super().iter_config_paths()

    def _parse_config_file(self, path: Path) -> list[str]:
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                data = json.load(f)
        except (OSError, ValueError) as exc:
            logger.warning("could not read %s: %s" % (path, exc))
            return []

        dirs = data.get("game_dirs", [])
        if not isinstance(dirs, list):
            return []
        return [str(d) for d in dirs if isinstance(d, str) and d]
