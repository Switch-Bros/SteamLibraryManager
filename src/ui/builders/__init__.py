"""UI Builder classes for Steam Library Manager.

Each builder is responsible for constructing a specific part of the UI.
"""

from __future__ import annotations

from src.ui.builders.central_widget_builder import CentralWidgetBuilder
from src.ui.builders.details_ui_builder import build_details_ui
from src.ui.builders.menu_builder import MenuBuilder
from src.ui.builders.statusbar_builder import StatusbarBuilder
from src.ui.builders.toolbar_builder import ToolbarBuilder

__all__ = [
    "MenuBuilder",
    "ToolbarBuilder",
    "StatusbarBuilder",
    "CentralWidgetBuilder",
    "build_details_ui",
]
