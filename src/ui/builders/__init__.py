# src/ui/builders/__init__.py

"""UI Builder classes for Steam Library Manager.

Each builder is responsible for constructing one section of the main window
(menu bar, toolbar, status bar).  They hold no persistent state beyond a
back-reference to MainWindow and are designed to be called once during
initial setup, or re-called when a language change requires a full rebuild.
"""

from src.ui.builders.menu_builder import MenuBuilder
from src.ui.builders.toolbar_builder import ToolbarBuilder
from src.ui.builders.statusbar_builder import StatusbarBuilder

__all__ = ["MenuBuilder", "ToolbarBuilder", "StatusbarBuilder"]