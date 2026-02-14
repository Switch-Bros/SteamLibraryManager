# src/ui/components/category_tree.py

"""
Displays games grouped by categories in a tree structure.

This widget provides the main navigation sidebar, showing games organized
by categories. It supports drag-and-drop for re-categorization and persists
the expanded/collapsed state of categories.
"""

from __future__ import annotations

from PyQt6.QtWidgets import QTreeWidget, QTreeWidgetItem, QAbstractItemView, QWidget
from PyQt6.QtCore import Qt, pyqtSignal, QPoint
from PyQt6.QtGui import QDragEnterEvent, QDragMoveEvent, QDropEvent

from src.core.game_manager import Game
from src.config import config
from src.utils.i18n import t


class GameTreeWidget(QTreeWidget):
    """
    Custom QTreeWidget for displaying and organizing game categories.

    Emits signals for user interactions like clicks, right-clicks, and
    selection changes. Handles drag-and-drop operations for moving games
    between categories.
    """

    # Signals
    game_clicked = pyqtSignal(Game)
    game_right_clicked = pyqtSignal(Game, QPoint)
    category_right_clicked = pyqtSignal(str, QPoint)
    selection_changed = pyqtSignal(list)  # list[Game]
    games_dropped = pyqtSignal(list, str)  # (list[Game], target_category)

    def __init__(self, parent: QWidget | None = None):
        """Initializes the GameTreeWidget."""
        super().__init__(parent)
        self.setHeaderHidden(True)
        self.setIndentation(20)
        self.setAlternatingRowColors(False)

        # Drag & Drop Setup
        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.setDragDropMode(QAbstractItemView.DragDropMode.DragDrop)
        self.setDefaultDropAction(Qt.DropAction.MoveAction)

        # Selection Mode
        self.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)

        # Connect internal signals
        self.itemClicked.connect(self._on_item_clicked)
        self.itemSelectionChanged.connect(self._on_selection_changed)
        self.itemExpanded.connect(self._on_item_expanded)
        self.itemCollapsed.connect(self._on_item_collapsed)

        # Style
        self.setStyleSheet("""
            QTreeWidget::item { padding: 4px; }
            QTreeWidget::item:selected { background-color: #2d5a88; }
        """)

    def set_loading_state(self, loading: bool) -> None:
        """Toggle the tree between a loading placeholder and normal state.

        Args:
            loading: If True, clears the tree and shows a disabled
                "Loading..." placeholder item. If False, just clears
                the tree so populate_categories() can refill it.
        """
        self.clear()
        if loading:
            placeholder = QTreeWidgetItem(self)
            placeholder.setText(0, t("common.loading"))
            placeholder.setFlags(Qt.ItemFlag.NoItemFlags)

    def populate_categories(
        self,
        categories: dict[str, list[Game]],
        dynamic_collections: set | None = None,
        duplicate_info: dict[str, tuple[str, int, int]] | None = None,
    ) -> None:
        """Rebuilds the entire tree with the provided category-to-game mapping.

        This method clears the existing tree and repopulates it, restoring the
        expansion state of each category from the application's config.

        Args:
            categories: A dictionary mapping category names to lists of Game objects.
                For duplicate collections, keys use ``__dup__<name>__<idx>`` format.
            dynamic_collections: Set of collection names that are dynamic
                (have filterSpec). These will get a blitz emoji.
            duplicate_info: Maps internal dup keys to (real_name, index, total).
                Used to display duplicate collections individually.
        """
        self.clear()

        if dynamic_collections is None:
            dynamic_collections = set()
        if duplicate_info is None:
            duplicate_info = {}

        for cat_name, games in categories.items():
            cat_item = QTreeWidgetItem(self)

            # Determine the real category name (for CRUD operations)
            real_name = cat_name
            is_duplicate = cat_name in duplicate_info

            if is_duplicate:
                real_name, idx, total = duplicate_info[cat_name]
                display_name = t(
                    "ui.categories.duplicate_indicator",
                    name=real_name,
                    index=idx,
                    total=total,
                )
            else:
                display_name = cat_name
                if cat_name in dynamic_collections:
                    display_name = f"{cat_name} {t('emoji.blitz')}"

            # Use i18n key for category count display
            cat_item.setText(0, t("ui.categories.category_count", name=display_name, count=len(games)))

            cat_item.setData(0, Qt.ItemDataRole.UserRole, "category")
            cat_item.setData(0, Qt.ItemDataRole.UserRole + 1, real_name)
            # Store the internal dup key so context menu can detect duplicates
            if is_duplicate:
                cat_item.setData(0, Qt.ItemDataRole.UserRole + 2, cat_name)

            # Use real_name for expansion state persistence
            cat_item.setExpanded(real_name in config.EXPANDED_CATEGORIES)

            for game in games:
                game_item = QTreeWidgetItem(cat_item)
                game_item.setText(0, game.name)

                game_item.setData(0, Qt.ItemDataRole.UserRole, "game")
                game_item.setData(0, Qt.ItemDataRole.UserRole + 1, game)

                # Use i18n key for the tooltip
                developer = game.developer if game.developer else t("common.unknown")
                game_item.setToolTip(0, t("ui.categories.game_tooltip", name=game.name, developer=developer))

    @staticmethod
    def _on_item_expanded(item: QTreeWidgetItem) -> None:
        """Saves the expanded state of a category to the config."""
        if item.data(0, Qt.ItemDataRole.UserRole) == "category":
            name = item.data(0, Qt.ItemDataRole.UserRole + 1)
            if name and name not in config.EXPANDED_CATEGORIES:
                config.EXPANDED_CATEGORIES.append(name)
                config.save()

    @staticmethod
    def _on_item_collapsed(item: QTreeWidgetItem) -> None:
        """Saves the collapsed state of a category to the config."""
        if item.data(0, Qt.ItemDataRole.UserRole) == "category":
            name = item.data(0, Qt.ItemDataRole.UserRole + 1)
            if name and name in config.EXPANDED_CATEGORIES:
                config.EXPANDED_CATEGORIES.remove(name)
                config.save()

    def _on_item_clicked(self, item: QTreeWidgetItem, _: int) -> None:
        """Emits a signal when a game item is clicked."""
        if item.data(0, Qt.ItemDataRole.UserRole) == "game":
            game = item.data(0, Qt.ItemDataRole.UserRole + 1)
            if game:
                self.game_clicked.emit(game)

    def _on_selection_changed(self) -> None:
        """Emits a signal with all currently selected game objects."""
        selected_games = [
            item.data(0, Qt.ItemDataRole.UserRole + 1)
            for item in self.selectedItems()
            if item.data(0, Qt.ItemDataRole.UserRole) == "game"
        ]
        self.selection_changed.emit(selected_games)

    def get_selected_categories(self) -> list[str]:
        """
        Returns a list of currently selected category names.

        Returns:
            list[str]: List of selected category names.
        """
        selected_categories = []
        for item in self.selectedItems():
            if item.data(0, Qt.ItemDataRole.UserRole) == "category":
                category_name = item.data(0, Qt.ItemDataRole.UserRole + 1)
                if category_name:
                    selected_categories.append(category_name)
        return selected_categories

    def contextMenuEvent(self, event) -> None:
        """Emits a signal when an item is right-clicked to show a context menu."""
        item = self.itemAt(event.pos())
        if not item:
            return

        item_type = item.data(0, Qt.ItemDataRole.UserRole)
        data = item.data(0, Qt.ItemDataRole.UserRole + 1)

        if item_type == "game" and data:
            self.game_right_clicked.emit(data, event.globalPos())
        elif item_type == "category" and data:
            # Check if multiple categories are selected
            selected_cats = self.get_selected_categories()
            if len(selected_cats) > 1:
                # Multi-category context menu (will be handled in main_window)
                self.category_right_clicked.emit("__MULTI__", event.globalPos())
            else:
                self.category_right_clicked.emit(data, event.globalPos())

    # The Drag & Drop events are kept simple as the main logic is often
    # handled in the controller/main window that receives the drop signal.
    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        if event.mimeData().hasFormat("application/x-qabstractitemmodeldatalist"):
            event.accept()
        else:
            event.ignore()

    def dragMoveEvent(self, event: QDragMoveEvent) -> None:
        item = self.itemAt(event.position().toPoint())
        # Only allow dropping onto category items
        if item and item.data(0, Qt.ItemDataRole.UserRole) == "category":
            event.accept()
        else:
            event.ignore()

    def dropEvent(self, event: QDropEvent) -> None:
        """
        Handles drop events when games are dragged onto categories.

        Emits the games_dropped signal with the dropped games and target category,
        allowing the parent window to update the VDF file.

        Args:
            event: The drop event containing drag data.
        """
        target_item = self.itemAt(event.position().toPoint())

        if not target_item or target_item.data(0, Qt.ItemDataRole.UserRole) != "category":
            event.ignore()
            return

        target_category = target_item.data(0, Qt.ItemDataRole.UserRole + 1)

        # Get all selected game items
        dropped_games = []
        for item in self.selectedItems():
            if item.data(0, Qt.ItemDataRole.UserRole) == "game":
                game = item.data(0, Qt.ItemDataRole.UserRole + 1)
                dropped_games.append(game)

        if dropped_games:
            # Emit signal before calling super() so parent can update data
            self.games_dropped.emit(dropped_games, target_category)

        super().dropEvent(event)
