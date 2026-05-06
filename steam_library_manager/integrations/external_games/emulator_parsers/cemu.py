#
# steam_library_manager/integrations/external_games/emulator_parsers/cemu.py
# Cemu (Wii U) emulator parser - XML config
#
# Copyright © 2025-2026 SwitchBros
# Licensed under the MIT License. See LICENSE for details.
#

from __future__ import annotations

import logging
import xml.etree.ElementTree as ET
from pathlib import Path

from steam_library_manager.integrations.external_games.emulator_parsers._base import BaseEmulatorParser

__all__ = ["CemuParser"]

logger = logging.getLogger("steamlibmgr.emulator_parsers.cemu")


class CemuParser(BaseEmulatorParser):
    """Cemu - Nintendo Wii U emulator. Reads <GamePaths> from settings.xml."""

    EMULATOR_NAME = "Cemu"
    EMULATOR_SYSTEMS = ("wiiu",)
    FLATPAK_ID = "info.cemu.Cemu"
    SYSTEM_BIN_NAMES = ("Cemu", "cemu", "Cemu.AppImage")
    NATIVE_CONFIG_REL = ("Cemu/settings.xml",)
    FLATPAK_CONFIG_REL = ("Cemu/settings.xml",)

    def __init__(self, config_path: Path | None = None) -> None:
        self._config_override = config_path

    def iter_config_paths(self):
        if self._config_override is not None:
            yield self._config_override
            return
        yield from super().iter_config_paths()

    def _parse_config_file(self, path: Path) -> list[str]:
        try:
            tree = ET.parse(path)
        except (ET.ParseError, OSError) as exc:
            logger.warning("could not parse %s: %s" % (path, exc))
            return []

        root = tree.getroot()
        # XPath: /content/GamePaths/Entry
        entries = root.findall("./GamePaths/Entry")
        return [e.text.strip() for e in entries if e.text and e.text.strip()]
