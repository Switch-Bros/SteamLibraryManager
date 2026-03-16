#
# steam_library_manager/integrations/external_games/shortcuts_vdf_parser.py
# Parser for existing non-Steam games in shortcuts.vdf
#
# Copyright © 2025-2026 SwitchBros
# Licensed under the MIT License. See LICENSE for details.
#

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from steam_library_manager.integrations.external_games.base_parser import BaseExternalParser
from steam_library_manager.integrations.external_games.models import ExternalGame

if TYPE_CHECKING:
    from pathlib import Path

    from steam_library_manager.core.shortcuts_manager import ShortcutsManager, SteamShortcut

__all__ = ["ShortcutsVDFParser"]

logger = logging.getLogger("steamlibmgr.external_games.shortcuts_vdf")


class ShortcutsVDFParser(BaseExternalParser):
    """Read existing non-Steam games from shortcuts.vdf."""

    def __init__(self, shortcuts_manager: ShortcutsManager) -> None:
        self._manager = shortcuts_manager

    def platform_name(self) -> str:
        return "Steam (Non-Steam)"

    def is_available(self) -> bool:
        return self._manager.get_shortcuts_path().exists()

    def get_config_paths(self) -> list[Path]:
        return [self._manager.get_shortcuts_path()]

    def read_games(self) -> list[ExternalGame]:
        """Read current shortcuts.vdf entries as ExternalGames."""
        shortcuts = self._manager.read_shortcuts()
        return [self._to_external_game(s) for s in shortcuts]

    @staticmethod
    def _to_external_game(shortcut: SteamShortcut) -> ExternalGame:
        exe = shortcut.exe.strip('"')

        return ExternalGame(
            platform="Steam (Non-Steam)",
            platform_app_id=str(shortcut.appid),
            name=shortcut.app_name,
            executable=exe,
            launch_command=shortcut.exe,
            platform_metadata=(
                ("start_dir", shortcut.start_dir),
                ("launch_options", shortcut.launch_options),
            ),
        )
