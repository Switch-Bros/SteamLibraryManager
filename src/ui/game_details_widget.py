"""
Game Details Widget - Split Layout: Details oben, Grid unten

Speichern als: src/ui/game_details_widget.py
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QFrame, QPushButton, QCheckBox, QScrollArea, QSizePolicy
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont
from typing import List, Dict
from src.core.game_manager import Game
from src.utils.i18n import t


class CategoryGrid(QWidget):
    """Grid für Kategorien (6 Spalten, scrollbar)"""

    category_toggled = pyqtSignal(str, bool)  # category, checked

    def __init__(self, parent=None):
        super().__init__(parent)
        self.categories = {}
        self.grid = QGridLayout(self)
        self.grid.setSpacing(8)
        self.grid.setContentsMargins(0, 0, 0, 0)
        self.columns = 6

    def set_categories(self, all_categories: List[str], game_categories: List[str]):
        """Setze Kategorien"""
        # Clear
        for cb in self.categories.values():
            cb.deleteLater()
        self.categories.clear()

        # Sort und add
        row, col = 0, 0
        for category in sorted(all_categories):
            if category == 'favorite':
                continue

            cb = QCheckBox(category)
            cb.setChecked(category in game_categories)
            cb.stateChanged.connect(
                lambda state, c=category: self.category_toggled.emit(
                    c, state == Qt.CheckState.Checked.value
                )
            )

            self.grid.addWidget(cb, row, col)
            self.categories[category] = cb

            col += 1
            if col >= self.columns:
                col = 0
                row += 1

        # Spacer am Ende
        self.grid.setRowStretch(row + 1, 1)


class GameDetailsWidget(QWidget):
    """Game Details: Oben = Info, Unten = Grid"""

    category_changed = pyqtSignal(str, str, bool)  # app_id, category, checked
    edit_metadata = pyqtSignal(object)  # game

    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_game = None
        self._create_ui()

    def _create_ui(self):
        """Create UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(8)

        # === TOP: Details Frame ===
        details_frame = QFrame()
        details_frame.setFrameStyle(QFrame.Shape.StyledPanel | QFrame.Shadow.Raised)
        details_layout = QVBoxLayout(details_frame)
        details_layout.setContentsMargins(10, 10, 10, 10)
        details_layout.setSpacing(5)

        # Name
        self.name_label = QLabel("Select a game")
        self.name_label.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        self.name_label.setWordWrap(True)
        details_layout.addWidget(self.name_label)

        # Separator
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setFrameShadow(QFrame.Shadow.Sunken)
        details_layout.addWidget(sep)

        # Info Grid (kompakt)
        info_grid = QGridLayout()
        info_grid.setSpacing(5)
        info_grid.setColumnStretch(1, 1)
        info_grid.setColumnStretch(3, 1)

        # Row 0: App ID | Playtime
        info_grid.addWidget(QLabel("<b>App ID:</b>"), 0, 0)
        self.app_id_label = QLabel("")
        info_grid.addWidget(self.app_id_label, 0, 1)

        info_grid.addWidget(QLabel("<b>" + t('ui.game_details.playtime') + ":</b>"), 0, 2)
        self.playtime_label = QLabel("")
        info_grid.addWidget(self.playtime_label, 0, 3)

        # Row 1: Developer | Publisher
        info_grid.addWidget(QLabel("<b>" + t('ui.game_details.developer') + ":</b>"), 1, 0)
        self.developer_label = QLabel("")
        self.developer_label.setWordWrap(True)
        info_grid.addWidget(self.developer_label, 1, 1)

        info_grid.addWidget(QLabel("<b>" + t('ui.game_details.publisher') + ":</b>"), 1, 2)
        self.publisher_label = QLabel("")
        self.publisher_label.setWordWrap(True)
        info_grid.addWidget(self.publisher_label, 1, 3)

        details_layout.addLayout(info_grid)

        # Edit Button
        edit_btn = QPushButton(f"✏️ {t('ui.game_details.edit_metadata')}")
        edit_btn.clicked.connect(self._on_edit)
        edit_btn.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        details_layout.addWidget(edit_btn)

        layout.addWidget(details_frame)

        # === BOTTOM: Categories Grid ===
        cat_frame = QFrame()
        cat_frame.setFrameStyle(QFrame.Shape.StyledPanel | QFrame.Shadow.Raised)
        cat_layout = QVBoxLayout(cat_frame)
        cat_layout.setContentsMargins(10, 10, 10, 10)
        cat_layout.setSpacing(5)

        # Header
        cat_header = QLabel(f"<b>{t('ui.game_details.categories_label')}</b>")
        cat_header.setFont(QFont("Arial", 12))
        cat_layout.addWidget(cat_header)

        # Scroll Area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        self.category_grid = CategoryGrid()
        self.category_grid.category_toggled.connect(self._on_category_toggle)
        scroll.setWidget(self.category_grid)

        cat_layout.addWidget(scroll)
        layout.addWidget(cat_frame)

        # Proportions: Details 30%, Categories 70%
        layout.setStretch(0, 3)
        layout.setStretch(1, 7)

    def set_game(self, game: Game, all_categories: List[str]):
        """Set current game"""
        self.current_game = game

        # Update info
        self.name_label.setText(game.name)
        self.app_id_label.setText(game.app_id)

        playtime = f"{game.playtime_hours}h" if game.playtime_hours > 0 else "Never played"
        self.playtime_label.setText(playtime)

        self.developer_label.setText(game.developer if game.developer else "—")
        self.publisher_label.setText(game.publisher if game.publisher else "—")

        # Update grid
        self.category_grid.set_categories(all_categories, game.categories)

    def clear(self):
        """Clear"""
        self.current_game = None
        self.name_label.setText("Select a game")
        self.app_id_label.setText("")
        self.playtime_label.setText("")
        self.developer_label.setText("")
        self.publisher_label.setText("")
        self.category_grid.set_categories([], [])

    def _on_category_toggle(self, category: str, checked: bool):
        """Category toggled"""
        if self.current_game:
            self.category_changed.emit(self.current_game.app_id, category, checked)

    def _on_edit(self):
        """Edit button"""
        if self.current_game:
            self.edit_metadata.emit(self.current_game)