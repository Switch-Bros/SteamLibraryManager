#
# steam_library_manager/integrations/external_games/shortcuts_vdf_parser.py
# Reads Steam shortcuts.vdf to find non-Steam games added via Steam
#
# Copyright © 2025-2026 SwitchBros
# Licensed under the MIT License. See LICENSE for details.
#

from __future__ import annotations

import logging

from steam_library_manager.integrations.external_games.base_parser import BaseExternalParser
from steam_library_manager.integrations.external_games.models import ExternalGame

__all__ = ["ShortcutsVDFParser"]

logger = logging.getLogger("steamlibmgr.external_games.shortcuts_vdf")


class ShortcutsVDFParser(BaseExternalParser):
    """Wraps ShortcutsManager so non-Steam games appear as ExternalGame objects.
    Mainly used for duplicate detection when adding new shortcuts.
    """

    def __init__(self, mgr):
        self._mgr = mgr

    def platform_name(self):
        return "Steam (Non-Steam)"

    def is_available(self):
        return self._mgr.get_shortcuts_path().exists()

    def get_config_paths(self):
        return [self._mgr.get_shortcuts_path()]

    def read_games(self):
        # read shortcuts.vdf and convert to ExternalGames
        lst = self._mgr.read_shortcuts()
        return [self._to_game(s) for s in lst]

    @staticmethod
    def _to_game(sc):
        # strip wrapping quotes for display
        exe = sc.exe.strip('"')

        return ExternalGame(
            platform="Steam (Non-Steam)",
            platform_app_id=str(sc.appid),
            name=sc.app_name,
            executable=exe,
            launch_command=sc.exe,
            platform_metadata=(
                ("start_dir", sc.start_dir),
                ("launch_options", sc.launch_options),
            ),
        )
