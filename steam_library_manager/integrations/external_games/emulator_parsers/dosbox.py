#
# steam_library_manager/integrations/external_games/emulator_parsers/dosbox.py
# DOSBox parser - no library config, presence-only detection
#
# Copyright © 2025-2026 SwitchBros
# Licensed under the MIT License. See LICENSE for details.
#

from __future__ import annotations

from steam_library_manager.integrations.external_games.emulator_parsers._base import BaseEmulatorParser

__all__ = ["DOSBoxParser"]


class DOSBoxParser(BaseEmulatorParser):
    """DOSBox - MS-DOS emulator. No library config; relies on user-added dirs."""

    EMULATOR_NAME = "DOSBox"
    EMULATOR_SYSTEMS = ("dos",)
    FLATPAK_ID = ""
    SYSTEM_BIN_NAMES = ("dosbox", "dosbox-staging", "dosbox-x")
    NATIVE_CONFIG_REL = ()
    FLATPAK_CONFIG_REL = ()

    def get_game_dirs(self):
        return []
