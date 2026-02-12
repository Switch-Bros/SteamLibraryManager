# src/ui/actions/__init__.py

"""UI Action Handler classes for Steam Library Manager.

Each handler is responsible for one menu or context-menu group.
They hold no persistent state beyond a back-reference to MainWindow
and are designed to extract action logic from the monolithic main_window.py.
"""

from __future__ import annotations

from src.ui.actions.file_actions import FileActions
from src.ui.actions.edit_actions import EditActions
from src.ui.actions.view_actions import ViewActions
from src.ui.actions.tools_actions import ToolsActions
from src.ui.actions.steam_actions import SteamActions
from src.ui.actions.game_actions import GameActions
from src.ui.actions.settings_actions import SettingsActions

# Export public classes
__all__ = [
    "FileActions",
    "EditActions",
    "ViewActions",
    "ToolsActions",
    "SteamActions",
    "GameActions",
    "SettingsActions",
]
