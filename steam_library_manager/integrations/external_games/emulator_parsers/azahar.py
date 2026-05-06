#
# steam_library_manager/integrations/external_games/emulator_parsers/azahar.py
# Azahar (3DS) emulator parser - Citra fork with Qt INI config
#
# Copyright © 2025-2026 SwitchBros
# Licensed under the MIT License. See LICENSE for details.
#

from __future__ import annotations

from pathlib import Path

from steam_library_manager.integrations.external_games.emulator_parsers._base import BaseEmulatorParser
from steam_library_manager.integrations.external_games.emulator_parsers._yuzu_qt_config import parse_yuzu_qt_gamedirs

__all__ = ["AzaharParser"]


class AzaharParser(BaseEmulatorParser):
    """Azahar - Nintendo 3DS emulator (Citra fork). Same INI schema as Eden."""

    EMULATOR_NAME = "Azahar"
    EMULATOR_SYSTEMS = ("3ds",)
    FLATPAK_ID = "io.github.azahar_emu.Azahar"
    SYSTEM_BIN_NAMES = ("azahar", "Azahar", "Azahar.AppImage")
    NATIVE_CONFIG_REL = ("azahar-emu/qt-config.ini",)
    FLATPAK_CONFIG_REL = ("azahar-emu/qt-config.ini",)

    def __init__(self, config_path: Path | None = None) -> None:
        self._config_override = config_path

    def iter_config_paths(self):
        if self._config_override is not None:
            yield self._config_override
            return
        yield from super().iter_config_paths()

    def _parse_config_file(self, path: Path) -> list[str]:
        return parse_yuzu_qt_gamedirs(path)
