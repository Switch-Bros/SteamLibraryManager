#
# steam_library_manager/integrations/external_games/emulator_parsers/citron.py
# Citron (Switch) emulator parser - Yuzu fork (discontinued Feb 2026)
#
# Copyright © 2025-2026 SwitchBros
# Licensed under the MIT License. See LICENSE for details.
#

from __future__ import annotations

from pathlib import Path

from steam_library_manager.integrations.external_games.emulator_parsers._base import BaseEmulatorParser
from steam_library_manager.integrations.external_games.emulator_parsers._yuzu_qt_config import parse_yuzu_qt_gamedirs

__all__ = ["CitronParser"]


class CitronParser(BaseEmulatorParser):
    """Citron - Nintendo Switch emulator (Yuzu fork, discontinued but still used)."""

    EMULATOR_NAME = "Citron"
    EMULATOR_SYSTEMS = ("switch",)
    FLATPAK_ID = ""  # not on Flathub
    SYSTEM_BIN_NAMES = ("citron", "Citron", "Citron.AppImage")
    NATIVE_CONFIG_REL = ("citron/qt-config.ini",)
    FLATPAK_CONFIG_REL = ()

    def __init__(self, config_path: Path | None = None) -> None:
        self._config_override = config_path

    def iter_config_paths(self):
        if self._config_override is not None:
            yield self._config_override
            return
        yield from super().iter_config_paths()

    def _parse_config_file(self, path: Path) -> list[str]:
        return parse_yuzu_qt_gamedirs(path)
