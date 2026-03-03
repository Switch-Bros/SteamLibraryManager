"""UI Builder classes for Steam Library Manager.

Each builder is responsible for constructing a specific part of the UI.
"""

from __future__ import annotations

from steam_library_manager.ui.builders.central_widget_builder import CentralWidgetBuilder
from steam_library_manager.ui.builders.details_ui_builder import build_details_ui
from steam_library_manager.ui.builders.menu_builder import MenuBuilder
from steam_library_manager.ui.builders.statusbar_builder import StatusbarBuilder
from steam_library_manager.ui.builders.toolbar_builder import ToolbarBuilder

__all__ = [
    "MenuBuilder",
    "ToolbarBuilder",
    "StatusbarBuilder",
    "CentralWidgetBuilder",
    "build_details_ui",
]
