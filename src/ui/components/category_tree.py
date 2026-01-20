"""
Category Tree - Clean & i18n-ready
Speichern als: src/ui/components/category_tree.py
"""

from PyQt6.QtWidgets import (
    QTreeWidget, QTreeWidgetItem, QWidget, QVBoxLayout,
    QHBoxLayout, QLabel, QPushButton, QFrame
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont
from typing import Optional, Callable, List, Dict
from src.utils.i18n import t


class GameTreeWidget(QTreeWidget):
    """Tree Widget mit Multi-Select und Spielen"""

    game_clicked = pyqtSignal(object)
    game_right_clicked = pyqtSignal(object, object)
    category_right_clicked = pyqtSignal(str, object)
    selection_changed = pyqtSignal(list)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setHeaderHidden(True)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self._on_context_menu)
        self.itemClicked.connect(self._on_item_clicked)
        self.setSelectionMode(QTreeWidget.SelectionMode.ExtendedSelection)
        self.itemSelectionChanged.connect(self._on_selection_changed)
        self.setAlternatingRowColors(True)
        self.setAnimated(True)

        # Styling
        self.setStyleSheet("""
            QTreeWidget {
                border: 1px solid palette(mid);
                border-radius: 4px;
            }
            QTreeWidget::item {
                padding: 4px;
            }
            QTreeWidget::item:hover {
                background-color: palette(light);
            }
            QTreeWidget::item:selected {
                background-color: palette(highlight);
                color: palette(highlighted-text);
            }
        """)

    def _on_selection_changed(self):
        """Handle selection changes"""
        selected_items = self.selectedItems()
        selected_games = []
        for item in selected_items:
            game = item.data(0, Qt.ItemDataRole.UserRole)
            if game and hasattr(game, 'app_id'):  # It's a Game object
                selected_games.append(game)
        self.selection_changed.emit(selected_games)

    def _on_item_clicked(self, item, column):
        """Handle item click"""
        game = item.data(0, Qt.ItemDataRole.UserRole)
        if game and hasattr(game, 'app_id'):  # It's a Game object
            self.game_clicked.emit(game)

    def _on_context_menu(self, pos):
        """Handle right-click context menu"""
        item = self.itemAt(pos)
        if not item:
            return

        game = item.data(0, Qt.ItemDataRole.UserRole)
        category = item.data(0, Qt.ItemDataRole.UserRole + 1)
        global_pos = self.viewport().mapToGlobal(pos)

        if game and hasattr(game, 'app_id'):
            self.game_right_clicked.emit(game, global_pos)
        elif category:
            self.category_right_clicked.emit(category, global_pos)

    def populate_categories(self, categories_data: Dict[str, List]):
        """
        Populate tree with categories and games
        """
        self.clear()

        folder_icon = t('ui.categories.icon_folder')
        fav_icon = t('ui.categories.icon_favorite')

        for category_name, games in categories_data.items():
            # Create category item
            # Format: "📁 Name (Count)"
            display_text = f"{folder_icon} {category_name} ({len(games)})"
            category_item = QTreeWidgetItem(self, [display_text])
            category_item.setData(0, Qt.ItemDataRole.UserRole + 1, category_name)

            # Style category
            font = category_item.font(0)
            font.setBold(True)
            font.setPointSize(11)
            category_item.setFont(0, font)

            # Add games (limit to first 100 for performance)
            display_limit = 100
            for game in games[:display_limit]:
                # Format: "  • GameName (Xh) ⭐"
                game_text = f"  • {game.name}"
                if game.playtime_hours > 0:
                    game_text += f" ({t('ui.game_details.hours', hours=game.playtime_hours)})"
                if game.is_favorite():
                    game_text += f" {fav_icon}"

                game_item = QTreeWidgetItem(category_item, [game_text])
                game_item.setData(0, Qt.ItemDataRole.UserRole, game)

                # Style game item
                game_font = game_item.font(0)
                game_font.setPointSize(10)
                game_item.setFont(0, game_font)

            # Show "... and X more" if there are more games
            if len(games) > display_limit:
                remaining = len(games) - display_limit
                more_text = t('ui.categories.more_games', count=remaining)

                more_item = QTreeWidgetItem(category_item, [more_text])
                more_font = more_item.font(0)
                more_font.setItalic(True)
                more_font.setPointSize(9)
                more_item.setFont(0, more_font)
                more_item.setForeground(0, Qt.GlobalColor.gray)

    def expand_all_categories(self):
        self.expandAll()

    def collapse_all_categories(self):
        self.collapseAll()


class CategoryTreeWithGames(QWidget):
    """
    Wrapper mit Header und Buttons
    DEPRECATED: But kept for compatibility if needed elsewhere
    """

    def __init__(self, parent=None, on_game_click: Optional[Callable] = None,
                 on_game_right_click: Optional[Callable] = None,
                 on_category_right_click: Optional[Callable] = None):
        super().__init__(parent)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)

        # Header
        header = QFrame()
        header.setFrameShape(QFrame.Shape.StyledPanel)
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(10, 5, 10, 5)

        # Title
        title = QLabel(t('ui.categories.title'))
        title_font = QFont()
        title_font.setPointSize(13)
        title_font.setBold(True)
        title.setFont(title_font)
        header_layout.addWidget(title)

        header_layout.addStretch()

        # Expand/Collapse buttons
        expand_btn = QPushButton(t('ui.categories.sym_expand'))
        expand_btn.setToolTip(t('ui.main.expand_all'))
        expand_btn.setMaximumWidth(40)
        expand_btn.clicked.connect(self._expand_all)
        header_layout.addWidget(expand_btn)

        collapse_btn = QPushButton(t('ui.categories.sym_collapse'))
        collapse_btn.setToolTip(t('ui.main.collapse_all'))
        collapse_btn.setMaximumWidth(40)
        collapse_btn.clicked.connect(self._collapse_all)
        header_layout.addWidget(collapse_btn)

        layout.addWidget(header)

        # Tree widget
        self.tree = GameTreeWidget()
        if on_game_click:
            self.tree.game_clicked.connect(on_game_click)
        if on_game_right_click:
            self.tree.game_right_clicked.connect(on_game_right_click)
        if on_category_right_click:
            self.tree.category_right_clicked.connect(on_category_right_click)

        layout.addWidget(self.tree)

    def _expand_all(self):
        self.tree.expand_all_categories()

    def _collapse_all(self):
        self.tree.collapse_all_categories()

    def add_category(self, name: str, icon: str, games: List):
        # icon ignored here, handled by tree populate
        categories_data = {name: games}
        self.tree.populate_categories(categories_data)

    def clear(self):
        self.tree.clear()

    def populate_categories(self, categories_data: Dict[str, List]):
        self.tree.populate_categories(categories_data)