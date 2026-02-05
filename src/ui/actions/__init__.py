# src/ui/actions/__init__.py

"""UI Action Handler classes for Steam Library Manager.

Each handler is responsible for one menu or context-menu group.
They hold no persistent state beyond a back-reference to MainWindow
and are designed to extract action logic from the monolithic main_window.py.
"""

from src.ui.actions.file_actions import FileActions
from src.ui.actions.edit_actions import EditActions
from src.ui.actions.view_actions import ViewActions
from .tools_actions import ToolsActions

# Export public classes
__all__ = [
    'FileActions',
    'EditActions',
    'ViewActions',
    'ToolsActions'
]