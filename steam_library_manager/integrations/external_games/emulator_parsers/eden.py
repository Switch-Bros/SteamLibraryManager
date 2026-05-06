#
# steam_library_manager/integrations/external_games/emulator_parsers/eden.py
# Eden (Switch) emulator parser - Yuzu fork with Qt INI config
#
# Copyright © 2025-2026 SwitchBros
# Licensed under the MIT License. See LICENSE for details.
#

from __future__ import annotations

from pathlib import Path

from steam_library_manager.integrations.external_games.emulator_parsers._base import BaseEmulatorParser
from steam_library_manager.integrations.external_games.emulator_parsers._yuzu_qt_config import parse_yuzu_qt_gamedirs

__all__ = ["EdenParser"]


class EdenParser(BaseEmulatorParser):
    """Eden - Nintendo Switch emulator (Yuzu fork)."""

    EMULATOR_NAME = "Eden"
    EMULATOR_SYSTEMS = ("switch",)
    FLATPAK_ID = "dev.eden_emu.eden"
    SYSTEM_BIN_NAMES = ("eden", "Eden", "Eden.AppImage")
    NATIVE_CONFIG_REL = ("eden/qt-config.ini",)
    FLATPAK_CONFIG_REL = ("eden/qt-config.ini",)

    def __init__(self, config_path: Path | None = None) -> None:
        # config_path override is for testing; production uses iter_config_paths()
        self._config_override = config_path

    def iter_config_paths(self):
        if self._config_override is not None:
            yield self._config_override
            return
        yield from super().iter_config_paths()

    def _parse_config_file(self, path: Path) -> list[str]:
        return parse_yuzu_qt_gamedirs(path)
