#
# steam_library_manager/integrations/external_games/emulator_parsers/melonds.py
# melonDS parser - no library config, presence-only detection
#
# Copyright © 2025-2026 SwitchBros
# Licensed under the MIT License. See LICENSE for details.
#

from __future__ import annotations

from steam_library_manager.integrations.external_games.emulator_parsers._base import BaseEmulatorParser

__all__ = ["MelonDSParser"]


class MelonDSParser(BaseEmulatorParser):
    """melonDS - Nintendo DS emulator. No library config to scrape;
    relies on user-added game dirs or EmuDeck hint fallback.
    """

    EMULATOR_NAME = "melonDS"
    EMULATOR_SYSTEMS = ("nds",)
    FLATPAK_ID = "net.kuribo64.melonDS"
    SYSTEM_BIN_NAMES = ("melonDS", "melonds")
    NATIVE_CONFIG_REL = ()
    FLATPAK_CONFIG_REL = ()

    def get_game_dirs(self):
        return []
