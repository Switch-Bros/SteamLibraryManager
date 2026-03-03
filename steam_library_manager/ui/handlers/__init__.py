"""UI action-handler package.

Each handler owns a logical slice of MainWindow's action methods.
They are instantiated once in MainWindow.__init__ and receive a
back-reference so they can call persistence helpers on the window.
"""

from __future__ import annotations

from steam_library_manager.ui.handlers.category_action_handler import CategoryActionHandler
from steam_library_manager.ui.handlers.selection_handler import SelectionHandler
from steam_library_manager.ui.handlers.category_change_handler import CategoryChangeHandler
from steam_library_manager.ui.handlers.data_load_handler import DataLoadHandler
from steam_library_manager.ui.handlers.empty_collection_handler import EmptyCollectionHandler
from steam_library_manager.ui.handlers.category_populator import CategoryPopulator
from steam_library_manager.ui.handlers.keyboard_handler import KeyboardHandler

__all__ = [
    "CategoryActionHandler",
    "SelectionHandler",
    "CategoryChangeHandler",
    "DataLoadHandler",
    "EmptyCollectionHandler",
    "CategoryPopulator",
    "KeyboardHandler",
]
