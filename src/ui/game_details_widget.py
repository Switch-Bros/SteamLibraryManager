"""
Game Details Widget - Fixed Layout & Signals
Speichern als: src/ui/game_details_widget.py
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QFrame, QPushButton, QCheckBox,
    QLineEdit, QListWidget, QListWidgetItem,
    QAbstractItemView, QMenu
)
from PyQt6.QtCore import Qt, pyqtSignal, QSize
from PyQt6.QtGui import QFont, QCursor
from typing import List
from src.core.game_manager import Game
from src.utils.i18n import t
from src.ui.components.clickable_image import ClickableImage
from src.core.steam_assets import SteamAssets
from src.ui.image_selection_dialog import ImageSelectionDialog


class InfoLabel(QLabel):
    def __init__(self, title_key, value=""):
        super().__init__()
        title = t(title_key)
        self.setText(f"<span style='color:#888;'>{title}:</span> <b>{value}</b>")
        self.setTextFormat(Qt.TextFormat.RichText)
        self.setStyleSheet("padding: 1px 0;")


class HorizontalCategoryList(QListWidget):
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
        self.setFixedHeight(190)

    def set_categories(self, all_categories: List[str], game_categories: List[str]):
        self.clear()
        if not all_categories:
            return
        for category in sorted(all_categories):
            if category == 'favorite':
                continue
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

        # === HEADER ===
        header_layout = QHBoxLayout()
        left_container = QVBoxLayout()

        self.name_label = QLabel(t('ui.game_details.select_placeholder'))
        self.name_label.setFont(QFont("Arial", 22, QFont.Weight.Bold))
        self.name_label.setWordWrap(True)
        self.name_label.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        left_container.addWidget(self.name_label)
        left_container.addStretch()

        button_layout = QHBoxLayout()
        button_layout.setSpacing(20)
        button_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)

        self.btn_store = QPushButton(t('ui.game_details.btn_store'))
        self.btn_store.clicked.connect(self._open_current_store)
        self.btn_store.setMinimumWidth(120)
        self.btn_edit = QPushButton(t('ui.game_details.btn_edit'))
        self.btn_edit.clicked.connect(self._on_edit)
        self.btn_edit.setMinimumWidth(120)

        button_layout.addWidget(self.btn_store)
        button_layout.addWidget(self.btn_edit)
        left_container.addLayout(button_layout)
        header_layout.addLayout(left_container, stretch=1)

        # === GALLERY ===
        gallery_widget = QWidget()
        gallery_widget.setFixedSize(600, 360)
        gallery_widget.setStyleSheet("background-color: #1a1a1a; border-radius: 4px;")
        gallery_layout = QGridLayout(gallery_widget)
        gallery_layout.setContentsMargins(4, 4, 4, 4)
        gallery_layout.setSpacing(4)

        # 1. Grid (Links, Hochkant)
        self.img_grid = ClickableImage('grids', 232, 348)
        # Explizite Typ-Übergabe via Lambda zur Sicherheit
        self.img_grid.clicked.connect(lambda: self._on_image_click('grids'))
        self.img_grid.right_clicked.connect(lambda: self._on_image_right_click('grids'))
        gallery_layout.addWidget(self.img_grid, 0, 0, 2, 1)

        # 2. Logo (Mitte Oben)
        logo_wrapper = QWidget()
        logo_layout = QVBoxLayout(logo_wrapper)
        logo_layout.setContentsMargins(0, 0, 0, 0)
        logo_layout.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter)
        self.img_logo = ClickableImage('logos', 176, 86)
        self.img_logo.clicked.connect(lambda: self._on_image_click('logos'))
        self.img_logo.right_clicked.connect(lambda: self._on_image_right_click('logos'))
        self.img_logo.setStyleSheet("background: transparent; border: 1px dashed #444;")
        logo_layout.addWidget(self.img_logo)
        gallery_layout.addWidget(logo_wrapper, 0, 1)

        # 3. Icon (Rechts Oben)
        icon_wrapper = QWidget()
        icon_layout = QVBoxLayout(icon_wrapper)
        icon_layout.setContentsMargins(0, 0, 0, 0)
        icon_layout.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignRight)
        self.img_icon = ClickableImage('icons', 168, 168)
        self.img_icon.clicked.connect(lambda: self._on_image_click('icons'))
        self.img_icon.right_clicked.connect(lambda: self._on_image_right_click('icons'))
        self.img_icon.setStyleSheet("background: transparent; border: none;")
        icon_layout.addWidget(self.img_icon)
        gallery_layout.addWidget(icon_wrapper, 0, 2)

        # 4. Hero (Unten Mitte/Rechts)
        hero_wrapper = QWidget()
        hero_layout = QVBoxLayout(hero_wrapper)
        hero_layout.setContentsMargins(0, 0, 0, 0)
        hero_layout.setAlignment(Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignHCenter)
        self.img_hero = ClickableImage('heroes', 348, 160)
        self.img_hero.clicked.connect(lambda: self._on_image_click('heroes'))
        self.img_hero.right_clicked.connect(lambda: self._on_image_right_click('heroes'))
        hero_layout.addWidget(self.img_hero)
        gallery_layout.addWidget(hero_wrapper, 1, 1, 1, 2)

        gallery_layout.setColumnStretch(0, 0)
        gallery_layout.setColumnStretch(1, 0)
        gallery_layout.setColumnStretch(2, 0)
        header_layout.addWidget(gallery_widget, alignment=Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignRight)
        main_layout.addLayout(header_layout)

        main_layout.addStretch()
        line1 = QFrame()
        line1.setFrameShape(QFrame.Shape.HLine)
        line1.setFrameShadow(QFrame.Shadow.Sunken)
        main_layout.addWidget(line1)

        # === METADATA ===
        meta_widget = QWidget()
        meta_grid = QGridLayout(meta_widget)
        meta_grid.setContentsMargins(0, 10, 0, 10)
        meta_grid.setHorizontalSpacing(30)
        meta_grid.setVerticalSpacing(5)
        meta_grid.setColumnMinimumWidth(0, 200)
        meta_grid.setColumnMinimumWidth(1, 200)
        meta_grid.setColumnMinimumWidth(2, 320)
        meta_grid.setColumnStretch(3, 1)

        meta_grid.addWidget(QLabel(f"<b>{t('ui.game_details.section_basic')}</b>"), 0, 0)
        self.lbl_appid = InfoLabel('ui.game_details.app_id')
        meta_grid.addWidget(self.lbl_appid, 1, 0)
        self.lbl_playtime = InfoLabel('ui.game_details.playtime')
        meta_grid.addWidget(self.lbl_playtime, 2, 0)
        self.lbl_updated = InfoLabel('ui.game_details.last_update', "—")
        meta_grid.addWidget(self.lbl_updated, 3, 0)

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

        meta_grid.addWidget(QLabel(f"<b>{t('ui.game_details.section_metadata')}</b>"), 0, 2)

        def add_meta_field(grid, label_key, row):
            l_layout = QHBoxLayout()
            l_lbl = QLabel(t(label_key) + ":")
            l_lbl.setStyleSheet("padding: 1px 0;")
            l_layout.addWidget(l_lbl)
            edit = QLineEdit()
            edit.setReadOnly(True)
            edit.setStyleSheet("background: transparent; border: none; font-weight: bold; padding: 1px 0;")
            l_layout.addWidget(edit)
            grid.addLayout(l_layout, row, 2)
            return edit

        self.edit_dev = add_meta_field(meta_grid, 'ui.game_details.developer', 1)
        self.edit_pub = add_meta_field(meta_grid, 'ui.game_details.publisher', 2)
        self.edit_rel = add_meta_field(meta_grid, 'ui.game_details.release_year', 3)

        main_layout.addWidget(meta_widget)

        line2 = QFrame()
        line2.setFrameShape(QFrame.Shape.HLine)
        line2.setFrameShadow(QFrame.Shadow.Sunken)
        line2.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(line2)

        # === CATEGORIES ===
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
            "platinum": "#B4C7D9", "gold": "#FDE100", "silver": "#C0C0C0",
            "bronze": "#CD7F32", "native": "#5CB85C", "borked": "#D9534F",
            "pending": "#1C39BB", "unknown": "#FE28A2"
        }
        color = colors.get(tier, "#FE28A2")
        display_text = t(f'ui.game_details.proton_tiers.{tier}')
        if display_text.startswith("["):
            display_text = tier.title()
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
        review_val = f"{game.review_score} ({game.review_count})" if game.review_score else "—"
        self.lbl_reviews.setText(
            f"<span style='color:#888;'>{t('ui.game_details.reviews')}:</span> <b>{review_val}</b>")
        unknown = t('ui.game_details.value_unknown')
        self.edit_dev.setText(game.developer if game.developer else unknown)
        self.edit_pub.setText(game.publisher if game.publisher else unknown)
        self.edit_rel.setText(game.release_year if game.release_year else unknown)
        self.category_list.set_categories(all_categories, game.categories)

        self._reload_images(game.app_id)

    def _reload_images(self, app_id: str):
        asset_map = {
            'grids': self.img_grid,
            'heroes': self.img_hero,
            'logos': self.img_logo,
            'icons': self.img_icon
        }
        for asset_type, img_widget in asset_map.items():
            img_widget.load_image(SteamAssets.get_asset_path(app_id, asset_type))

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

    def _on_image_click(self, img_type: str):
        """Öffnet den Dialog für den spezifischen Bildtyp"""
        if not self.current_game:
            return

        # Hier übergeben wir img_type exakt an den Dialog
        dialog = ImageSelectionDialog(self, self.current_game.name, self.current_game.app_id, img_type)
        if dialog.exec():
            url = dialog.get_selected_url()
            if url and SteamAssets.save_custom_image(self.current_game.app_id, img_type, url):
                self._reload_single_asset(img_type)

    def _on_image_right_click(self, img_type: str):
        if not self.current_game:
            return

        menu = QMenu(self)
        reset_action = menu.addAction(t('ui.game_details.gallery.reset'))
        action = menu.exec(QCursor.pos())

        if action == reset_action and SteamAssets.delete_custom_image(self.current_game.app_id, img_type):
            self._reload_single_asset(img_type)

    def _reload_single_asset(self, img_type: str):
        asset_map = {
            'grids': self.img_grid,
            'heroes': self.img_hero,
            'logos': self.img_logo,
            'icons': self.img_icon
        }
        if img_type in asset_map:
            path = SteamAssets.get_asset_path(self.current_game.app_id, img_type)
            asset_map[img_type].load_image(path)