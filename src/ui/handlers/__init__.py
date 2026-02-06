# src/ui/handlers/__init__.py

"""UI action-handler package.

Each handler owns a logical slice of MainWindow's action methods.
They are instantiated once in MainWindow.__init__ and receive a
back-reference so they can call persistence helpers on the window.
"""

from src.ui.handlers.category_action_handler import CategoryActionHandler
from src.ui.handlers.selection_handler import SelectionHandler
from src.ui.handlers.category_change_handler import CategoryChangeHandler

__all__: list[str] = [
    "CategoryActionHandler",
    "SelectionHandler",
    "CategoryChangeHandler",
]

# Hallo Sarah dies ist ein Test ob du die Datei findest in der ich dich grüße ;)