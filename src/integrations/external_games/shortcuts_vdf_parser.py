"""Parser for existing non-Steam games in shortcuts.vdf.

Wraps ShortcutsManager for duplicate detection. Does NOT
duplicate VDF parsing logic — delegates to ShortcutsManager.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from src.integrations.external_games.base_parser import BaseExternalParser
from src.integrations.external_games.models import ExternalGame

if TYPE_CHECKING:
    from pathlib import Path

    from src.core.shortcuts_manager import ShortcutsManager, SteamShortcut

__all__ = ["ShortcutsVDFParser"]

logger = logging.getLogger("steamlibmgr.external_games.shortcuts_vdf")


class ShortcutsVDFParser(BaseExternalParser):
    """Read existing non-Steam games from shortcuts.vdf.

    Wraps ShortcutsManager for uniform ExternalGame interface.
    Used for duplicate detection when adding new shortcuts.
    """

    def __init__(self, shortcuts_manager: ShortcutsManager) -> None:
        """Initializes the parser.

        Args:
            shortcuts_manager: Configured ShortcutsManager instance.
        """
        self._manager = shortcuts_manager

    def platform_name(self) -> str:
        """Return platform name.

        Returns:
            Platform identifier.
        """
        return "Steam (Non-Steam)"

    def is_available(self) -> bool:
        """Check if shortcuts.vdf exists.

        Returns:
            True if the file is present.
        """
        return self._manager.get_shortcuts_path().exists()

    def get_config_paths(self) -> list[Path]:
        """Return shortcuts.vdf path.

        Returns:
            Single-element list with the shortcuts file path.
        """
        return [self._manager.get_shortcuts_path()]

    def read_games(self) -> list[ExternalGame]:
        """Read current shortcuts.vdf entries as ExternalGames.

        Delegates to ShortcutsManager.read_shortcuts() internally,
        then converts SteamShortcut to ExternalGame.

        Returns:
            List of existing non-Steam game entries.
        """
        shortcuts = self._manager.read_shortcuts()
        return [self._to_external_game(s) for s in shortcuts]

    @staticmethod
    def _to_external_game(shortcut: SteamShortcut) -> ExternalGame:
        """Convert a SteamShortcut to ExternalGame.

        Args:
            shortcut: SteamShortcut from shortcuts.vdf.

        Returns:
            ExternalGame representation.
        """
        # Strip quotes from exe for display
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
