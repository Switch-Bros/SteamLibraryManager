"""
Category Tree Widget - Left Sidebar Navigation
Displays games grouped by categories/collections with Drag & Drop support.
"""
from typing import Dict, List, Optional

from PyQt6.QtWidgets import (
    QTreeWidget, QTreeWidgetItem, QAbstractItemView,
    QWidget
)
from PyQt6.QtCore import Qt, pyqtSignal, QPoint
from PyQt6.QtGui import QDragEnterEvent, QDropEvent

from src.core.game_manager import Game
from src.config import config


class GameTreeWidget(QTreeWidget):
    """
    Custom TreeWidget handling game categories and drag-and-drop organization.
    Remembers expanded/collapsed state via Config.
    """
    # Signals
    game_clicked = pyqtSignal(Game)
    game_right_clicked = pyqtSignal(Game, QPoint)
    category_right_clicked = pyqtSignal(str, QPoint)
    selection_changed = pyqtSignal(list)  # List[Game]

    def __init__(self, parent: Optional[QWidget] = None):
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
        # noinspection PyUnresolvedReferences
        self.itemClicked.connect(self._on_item_clicked)
        # noinspection PyUnresolvedReferences
        self.itemSelectionChanged.connect(self._on_selection_changed)

        # Connect Expansion Signals for State Persistence
        # noinspection PyUnresolvedReferences
        self.itemExpanded.connect(self._on_item_expanded)
        # noinspection PyUnresolvedReferences
        self.itemCollapsed.connect(self._on_item_collapsed)

        # Style
        self.setStyleSheet("""
            QTreeWidget::item { padding: 4px; }
            QTreeWidget::item:selected { background-color: #2d5a88; }
        """)

    def populate_categories(self, categories: Dict[str, List[Game]]) -> None:
        """
        Rebuilds the tree with the provided category mapping.
        Restores expansion state from config.
        """
        self.clear()

        for cat_name, games in categories.items():
            cat_item = QTreeWidgetItem(self)
            cat_item.setText(0, f"{cat_name} ({len(games)})")

            # Store category name in data
            cat_item.setData(0, Qt.ItemDataRole.UserRole, "category")
            cat_item.setData(0, Qt.ItemDataRole.UserRole + 1, cat_name)

            # Check state in config
            if cat_name in config.EXPANDED_CATEGORIES:
                cat_item.setExpanded(True)
            else:
                cat_item.setExpanded(False)  # Default: Collapsed

            for game in games:
                game_item = QTreeWidgetItem(cat_item)
                game_item.setText(0, game.name)

                # Store Game object
                game_item.setData(0, Qt.ItemDataRole.UserRole, "game")
                game_item.setData(0, Qt.ItemDataRole.UserRole + 1, game)

                # Tooltip
                game_item.setToolTip(0, f"{game.name}\n{game.developer or ''}")

    @staticmethod
    def _on_item_expanded(item: QTreeWidgetItem) -> None:
        """Save expanded state."""
        if item.data(0, Qt.ItemDataRole.UserRole) == "category":
            name = item.data(0, Qt.ItemDataRole.UserRole + 1)
            if name and name not in config.EXPANDED_CATEGORIES:
                config.EXPANDED_CATEGORIES.append(name)
                config.save()

    @staticmethod
    def _on_item_collapsed(item: QTreeWidgetItem) -> None:
        """Save collapsed state."""
        if item.data(0, Qt.ItemDataRole.UserRole) == "category":
            name = item.data(0, Qt.ItemDataRole.UserRole + 1)
            if name and name in config.EXPANDED_CATEGORIES:
                config.EXPANDED_CATEGORIES.remove(name)
                config.save()

    def _on_item_clicked(self, item: QTreeWidgetItem, _: int) -> None:
        """Handle single clicks."""
        item_type = item.data(0, Qt.ItemDataRole.UserRole)

        if item_type == "game":
            game = item.data(0, Qt.ItemDataRole.UserRole + 1)
            if game:
                self.game_clicked.emit(game)

    def _on_selection_changed(self) -> None:
        """Handle multi-selection."""
        selected_games = []
        for item in self.selectedItems():
            item_type = item.data(0, Qt.ItemDataRole.UserRole)
            if item_type == "game":
                game = item.data(0, Qt.ItemDataRole.UserRole + 1)
                if game:
                    selected_games.append(game)

        if selected_games:
            self.selection_changed.emit(selected_games)

    # --- Drag & Drop Events ---

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        if event.mimeData().hasFormat("application/x-qabstractitemmodeldatalist"):
            event.accept()
        else:
            event.ignore()

    def dragMoveEvent(self, event: QDragEnterEvent) -> None:
        item = self.itemAt(event.position().toPoint())
        if item:
            # Only allow drop on Categories
            item_type = item.data(0, Qt.ItemDataRole.UserRole)
            if item_type == "category":
                event.accept()
                return
        event.ignore()

    def dropEvent(self, event: QDropEvent) -> None:
        if event.source() == self:
            target_item = self.itemAt(event.position().toPoint())
            if target_item:
                # Logic to process move handled by signals/controller
                pass

        super().dropEvent(event)

    # --- Context Menu ---

    def contextMenuEvent(self, event) -> None:
        """Show context menu on right click."""
        item = self.itemAt(event.pos())
        if not item: return

        item_type = item.data(0, Qt.ItemDataRole.UserRole)
        data = item.data(0, Qt.ItemDataRole.UserRole + 1)

        if item_type == "game":
            self.game_right_clicked.emit(data, event.globalPos())

        elif item_type == "category":
            self.category_right_clicked.emit(data, event.globalPos())