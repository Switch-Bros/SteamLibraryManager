"""
Game Details Widget - Fixed Layout & Crash Fix (setColumnMinimumWidth)
Speichern als: src/ui/game_details_widget.py
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QFrame, QPushButton, QCheckBox, QScrollArea,
    QSizePolicy, QLineEdit, QListWidget, QListWidgetItem,
    QAbstractItemView
)
from PyQt6.QtCore import Qt, pyqtSignal, QSize
from PyQt6.QtGui import QFont, QPixmap, QColor
from typing import List
from src.core.game_manager import Game
from src.utils.i18n import t


class InfoLabel(QLabel):
    """Kleines Hilfs-Label für fette Titel"""

    def __init__(self, title_key, value="", is_i18n_key=False):
        super().__init__()
        title = t(title_key)
        self.setText(f"<span style='color:#888;'>{title}:</span> <b>{value}</b>")
        self.setTextFormat(Qt.TextFormat.RichText)
        self.setStyleSheet("padding: 1px 0;")


class HorizontalCategoryList(QListWidget):
    """Horizontale Liste für Kategorien"""
    category_toggled = pyqtSignal(str, bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setViewMode(QListWidget.ViewMode.IconMode)
        self.setFlow(QListWidget.Flow.TopToBottom)
        self.setWrapping(True)
        self.setResizeMode(QListWidget.ResizeMode.Adjust)
        self.setSpacing(4)
        self.setUniformItemSizes(True)
        self.setMovement(QListWidget.Movement.Static)
        self.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setFixedHeight(220)

    def set_categories(self, all_categories: List[str], game_categories: List[str]):
        self.clear()
        if not all_categories: return

        for category in sorted(all_categories):
            if category == 'favorite': continue

            item = QListWidgetItem(self)
            item.setSizeHint(QSize(200, 24))

            cb = QCheckBox(category)
            cb.setChecked(category in game_categories)
            cb.setStyleSheet("QCheckBox { font-size: 11px; margin-left: 2px; }")
            cb.stateChanged.connect(
                lambda state, c=category: self.category_toggled.emit(c, state == Qt.CheckState.Checked.value)
            )

            self.setItemWidget(item, cb)


class GameDetailsWidget(QWidget):
    category_changed = pyqtSignal(str, str, bool)
    edit_metadata = pyqtSignal(object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_game = None
        self._create_ui()

    def _create_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(15, 15, 15, 0)
        main_layout.setSpacing(0)

        # 1. HEADER
        header_layout = QHBoxLayout()

        title_block = QVBoxLayout()
        self.name_label = QLabel(t('ui.game_details.select_placeholder'))
        self.name_label.setFont(QFont("Arial", 22, QFont.Weight.Bold))
        self.name_label.setWordWrap(True)
        title_block.addWidget(self.name_label, alignment=Qt.AlignmentFlag.AlignTop)

        action_layout = QHBoxLayout()
        self.btn_store = QPushButton(t('ui.game_details.btn_store'))
        self.btn_store.clicked.connect(self._open_current_store)
        self.btn_edit = QPushButton(t('ui.game_details.btn_edit'))
        self.btn_edit.clicked.connect(self._on_edit)
        action_layout.addWidget(self.btn_store)
        action_layout.addWidget(self.btn_edit)
        action_layout.addStretch()

        title_block.addLayout(action_layout)
        header_layout.addLayout(title_block, stretch=1)

        self.image_label = QLabel(t('ui.game_details.cover_placeholder'))
        self.image_label.setFixedSize(240, 120)
        self.image_label.setStyleSheet("background-color: #333; border: 1px solid #555; color: #888;")
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header_layout.addWidget(self.image_label, alignment=Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignRight)

        main_layout.addLayout(header_layout)

        # PLATZHALTER (Drückt alles nach unten)
        main_layout.addStretch()

        line1 = QFrame()
        line1.setFrameShape(QFrame.Shape.HLine)
        line1.setFrameShadow(QFrame.Shadow.Sunken)
        main_layout.addWidget(line1)

        # 2. METADATA GRID
        meta_widget = QWidget()
        meta_grid = QGridLayout(meta_widget)
        meta_grid.setContentsMargins(0, 10, 0, 10)
        meta_grid.setHorizontalSpacing(30)
        meta_grid.setVerticalSpacing(5)

        # FIX: Hier war der Fehler! 'setColumnMinimumWidth' statt 'setColumnFixedWidth'
        meta_grid.setColumnMinimumWidth(0, 180)  # Basic Info
        meta_grid.setColumnMinimumWidth(1, 180)  # Ratings
        meta_grid.setColumnMinimumWidth(2, 340)  # Metadata

        # Leere Spalte rechts füllt den Rest auf
        meta_grid.setColumnStretch(3, 1)

        # Col 1
        meta_grid.addWidget(QLabel(f"<b>{t('ui.game_details.section_basic')}</b>"), 0, 0)
        self.lbl_appid = InfoLabel('ui.game_details.app_id')
        meta_grid.addWidget(self.lbl_appid, 1, 0)
        self.lbl_playtime = InfoLabel('ui.game_details.playtime')
        meta_grid.addWidget(self.lbl_playtime, 2, 0)
        self.lbl_updated = InfoLabel('ui.game_details.last_update', "—")
        meta_grid.addWidget(self.lbl_updated, 3, 0)

        # Col 2
        meta_grid.addWidget(QLabel(f"<b>{t('ui.game_details.section_ratings')}</b>"), 0, 1)

        self.lbl_proton = QLabel()
        self.lbl_proton.setTextFormat(Qt.TextFormat.RichText)
        self.lbl_proton.setStyleSheet("padding: 1px 0;")
        self._update_proton_label("unknown")
        meta_grid.addWidget(self.lbl_proton, 1, 1)

        self.lbl_steamdb = InfoLabel('ui.game_details.steam_db', "—")
        meta_grid.addWidget(self.lbl_steamdb, 2, 1)
        self.lbl_reviews = InfoLabel('ui.game_details.reviews', "—")
        meta_grid.addWidget(self.lbl_reviews, 3, 1)

        # Col 3
        meta_grid.addWidget(QLabel(f"<b>{t('ui.game_details.section_metadata')}</b>"), 0, 2)

        dev_layout = QHBoxLayout()
        dev_layout.setContentsMargins(0, 0, 0, 0)
        dev_lbl = QLabel(t('ui.game_details.developer') + ":")
        dev_lbl.setStyleSheet("padding: 1px 0;")
        dev_layout.addWidget(dev_lbl)
        self.edit_dev = QLineEdit()
        self.edit_dev.setReadOnly(True)
        self.edit_dev.setStyleSheet("background: transparent; border: none; font-weight: bold; padding: 1px 0;")
        dev_layout.addWidget(self.edit_dev)
        meta_grid.addLayout(dev_layout, 1, 2)

        pub_layout = QHBoxLayout()
        pub_layout.setContentsMargins(0, 0, 0, 0)
        pub_lbl = QLabel(t('ui.game_details.publisher') + ":")
        pub_lbl.setStyleSheet("padding: 1px 0;")
        pub_layout.addWidget(pub_lbl)
        self.edit_pub = QLineEdit()
        self.edit_pub.setReadOnly(True)
        self.edit_pub.setStyleSheet("background: transparent; border: none; font-weight: bold; padding: 1px 0;")
        pub_layout.addWidget(self.edit_pub)
        meta_grid.addLayout(pub_layout, 2, 2)

        rel_layout = QHBoxLayout()
        rel_layout.setContentsMargins(0, 0, 0, 0)
        rel_lbl = QLabel(t('ui.game_details.release_year') + ":")
        rel_lbl.setStyleSheet("padding: 1px 0;")
        rel_layout.addWidget(rel_lbl)
        self.edit_rel = QLineEdit()
        self.edit_rel.setReadOnly(True)
        self.edit_rel.setStyleSheet("background: transparent; border: none; font-weight: bold; padding: 1px 0;")
        rel_layout.addWidget(self.edit_rel)
        meta_grid.addLayout(rel_layout, 3, 2)

        main_layout.addWidget(meta_widget)

        line2 = QFrame()
        line2.setFrameShape(QFrame.Shape.HLine)
        line2.setFrameShadow(QFrame.Shadow.Sunken)
        line2.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(line2)

        # 3. CATEGORY LIST
        cat_header = QLabel(t('ui.game_details.categories_label'))
        cat_header.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        cat_header.setStyleSheet("padding-top: 5px; padding-bottom: 5px;")
        main_layout.addWidget(cat_header)

        self.category_list = HorizontalCategoryList()
        self.category_list.category_toggled.connect(self._on_category_toggle)
        main_layout.addWidget(self.category_list)

    def _update_proton_label(self, tier: str):
        tier = tier.lower() if tier else "unknown"
        colors = {
            "platinum": "#B4C7D9",
            "gold": "#FDE100",
            "silver": "#C0C0C0",
            "bronze": "#CD7F32",
            "native": "#5CB85C",
            "borked": "#D9534F",
            "pending": "#1C39BB",
            "unknown": "#FE28A2"
        }
        color = colors.get(tier, "#1C39BB")
        display_text = t(f'ui.game_details.proton_tiers.{tier}')
        if display_text.startswith("["): display_text = tier.title()

        title = t('ui.game_details.proton_db')
        self.lbl_proton.setText(
            f"<span style='color:#888;'>{title}:</span> <span style='color:{color}; font-weight:bold;'>{display_text}</span>")

    def set_game(self, game: Game, all_categories: List[str]):
        self.current_game = game

        self.name_label.setText(game.name)

        self.lbl_appid.setText(f"<span style='color:#888;'>{t('ui.game_details.app_id')}:</span> <b>{game.app_id}</b>")

        playtime_val = f"{game.playtime_hours}h" if game.playtime_hours > 0 else t('ui.game_details.never_played')
        self.lbl_playtime.setText(
            f"<span style='color:#888;'>{t('ui.game_details.playtime')}:</span> <b>{playtime_val}</b>")

        update_val = game.last_updated if game.last_updated else "—"
        self.lbl_updated.setText(
            f"<span style='color:#888;'>{t('ui.game_details.last_update')}:</span> <b>{update_val}</b>")

        self._update_proton_label(game.proton_db_rating)

        db_val = game.steam_db_rating if game.steam_db_rating else "—"
        self.lbl_steamdb.setText(f"<span style='color:#888;'>{t('ui.game_details.steam_db')}:</span> <b>{db_val}</b>")

        if game.review_score:
            review_val = f"{game.review_score} ({game.review_count})"
        else:
            review_val = "—"
        self.lbl_reviews.setText(
            f"<span style='color:#888;'>{t('ui.game_details.reviews')}:</span> <b>{review_val}</b>")

        unknown = t('ui.game_details.value_unknown')
        self.edit_dev.setText(game.developer if game.developer else unknown)
        self.edit_pub.setText(game.publisher if game.publisher else unknown)
        self.edit_rel.setText(game.release_year if game.release_year else unknown)

        self.category_list.set_categories(all_categories, game.categories)

    def clear(self):
        self.current_game = None
        self.name_label.setText(t('ui.game_details.select_placeholder'))
        self._update_proton_label("unknown")
        self.category_list.set_categories([], [])

    def _on_category_toggle(self, category: str, checked: bool):
        if self.current_game:
            self.category_changed.emit(self.current_game.app_id, category, checked)

    def _on_edit(self):
        if self.current_game:
            self.edit_metadata.emit(self.current_game)

    def _open_current_store(self):
        if self.current_game:
            import webbrowser
            webbrowser.open(f"https://store.steampowered.com/app/{self.current_game.app_id}")