# src/ui/game_details_widget.py

"""
Widget for displaying and editing game details.

This module provides a comprehensive widget that displays game information
including metadata, images (grid, hero, logo, icon), ratings, and categories.
It allows users to edit metadata, change images, and toggle categories.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QFrame, QPushButton, QCheckBox,
    QLineEdit, QListWidget, QListWidgetItem,
    QAbstractItemView, QMenu, QDialog
)

from PyQt6.QtCore import Qt, pyqtSignal, QSize
from PyQt6.QtGui import QFont, QCursor
from typing import List
from pathlib import Path
from src.core.game_manager import Game
from src.utils.i18n import t
from src.utils.date_utils import format_timestamp_to_date
from src.ui.components.clickable_image import ClickableImage
from src.core.steam_assets import SteamAssets
from src.ui.image_selection_dialog import ImageSelectionDialog


class InfoLabel(QLabel):
    """
    Custom label for displaying key-value pairs with styled formatting.

    This label displays a title in gray and a value in bold, formatted as HTML.
    """

    def __init__(self, title_key: str, value: str = ""):
        """
        Initializes the info label.

        Args:
            title_key (str): The translation key for the title.
            value (str): The value to display. Defaults to empty string.
        """
        super().__init__()
        title = t(title_key)
        self.setText(f"<span style='color:#888;'>{title}:</span> <b>{value}</b>")
        self.setTextFormat(Qt.TextFormat.RichText)
        self.setStyleSheet("padding: 1px 0;")


class HorizontalCategoryList(QListWidget):
    """
    Custom list widget for displaying game categories as checkboxes.

    This widget displays categories in a horizontal, wrapping layout with
    checkboxes that can be toggled to add or remove categories from a game.

    Signals:
        category_toggled (str, bool): Emitted when a category checkbox is toggled,
                                      passes the category name and checked state.
    """

    category_toggled = pyqtSignal(str, bool)

    def __init__(self, parent=None):
        """
        Initializes the horizontal category list.

        Args:
            parent: Parent widget. Defaults to None.
        """
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

        # Prevent stealing focus from game tree
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        # For multi-select mode
        self.games_categories = []

    def set_categories(self, all_categories: List[str], game_categories: List[str]):
        """
        Sets the categories to display and marks which ones are assigned to the game.

        Args:
            all_categories (List[str]): List of all available categories.
            game_categories (List[str]): List of categories assigned to the current game.
        """
        self.clear()
        if not all_categories:
            return
        for category in sorted(all_categories):
            if category == 'favorite':
                continue
            item = QListWidgetItem(self)
            item.setSizeHint(QSize(200, 24))
            # Escape & to && for Qt (otherwise & becomes keyboard shortcut)
            display_name = category.replace('&', '&&')
            cb = QCheckBox(display_name)
            cb.setChecked(category in game_categories)
            cb.setFocusPolicy(Qt.FocusPolicy.NoFocus)  # Prevent focus stealing
            cb.setStyleSheet("QCheckBox { font-size: 11px; margin-left: 2px; }")
            cb.stateChanged.connect(
                lambda state, c=category: self.category_toggled.emit(c, state == Qt.CheckState.Checked.value)
            )
            self.setItemWidget(item, cb)

    def set_categories_multi(self, all_categories: List[str], games_categories: List[List[str]]):
        """
        Sets categories for multiple games with tri-state checkboxes.

        Checkbox states:
        - Unchecked (empty): No game has this category
        - PartiallyChecked (gray): Some games have this category
        - Checked (gold): All games have this category

        Args:
            all_categories (List[str]): List of all available categories.
            games_categories (List[List[str]]): List of category lists, one per game.
        """
        self.clear()
        if not all_categories or not games_categories:
            return

        # Store games_categories for later reference
        self.games_categories = games_categories
        total_games = len(games_categories)

        for category in sorted(all_categories):
            if category == 'favorite':
                continue

            # Count how many games have this category
            count = sum(1 for game_cats in games_categories if category in game_cats)

            item = QListWidgetItem(self)
            item.setSizeHint(QSize(200, 24))
            # Escape & to && for Qt (otherwise & becomes keyboard shortcut)
            display_name = category.replace('&', '&&')
            cb = QCheckBox(display_name)
            cb.setTristate(True)  # Enable tri-state
            cb.setFocusPolicy(Qt.FocusPolicy.NoFocus)  # Prevent focus stealing

            # Set tri-state based on count
            if count == 0:
                cb.setCheckState(Qt.CheckState.Unchecked)
                cb.setStyleSheet("QCheckBox { font-size: 11px; margin-left: 2px; }")
            elif count == total_games:
                cb.setCheckState(Qt.CheckState.Checked)
                cb.setStyleSheet("QCheckBox { font-size: 11px; margin-left: 2px; color: #FFD700; font-weight: bold; }")
            else:
                cb.setCheckState(Qt.CheckState.PartiallyChecked)
                cb.setStyleSheet("QCheckBox { font-size: 11px; margin-left: 2px; color: #888888; }")

            # Store the current state in the checkbox for reference
            cb.setProperty('category', category)
            cb.setProperty('previous_state', cb.checkState())

            # Use clicked signal instead of stateChanged to have more control
            cb.clicked.connect(lambda checked=None, checkbox=cb: self._handle_tristate_click(checkbox))
            self.setItemWidget(item, cb)

    def _handle_tristate_click(self, checkbox: QCheckBox):
        """
        Handles tri-state checkbox click logic.

        Logic:
        - Unchecked → Checked (add to all)
        - PartiallyChecked → Checked (add to all)
        - Checked → Unchecked (remove from all)

        Args:
            checkbox: The checkbox that was clicked.
        """
        category = checkbox.property('category')
        previous_state = checkbox.property('previous_state')

        # Determine the desired action based on previous state
        if previous_state == Qt.CheckState.Checked:
            # Was checked (gold) → Make unchecked (empty)
            checkbox.setCheckState(Qt.CheckState.Unchecked)
            checkbox.setStyleSheet("QCheckBox { font-size: 11px; margin-left: 2px; }")
            new_state = Qt.CheckState.Unchecked
            checked = False
        else:
            # Was unchecked or partial → Make checked (gold)
            checkbox.setCheckState(Qt.CheckState.Checked)
            checkbox.setStyleSheet(
                "QCheckBox { font-size: 11px; margin-left: 2px; color: #FFD700; font-weight: bold; }")
            new_state = Qt.CheckState.Checked
            checked = True

        # Update the stored previous state
        checkbox.setProperty('previous_state', new_state)
        
        # Emit signal (will be handled by _on_category_toggle in GameDetailsWidget)
        self.category_toggled.emit(category, checked)


class GameDetailsWidget(QWidget):
    """
    Widget for displaying and editing detailed game information.

    This widget shows comprehensive game details including metadata, images,
    ratings, and categories. It allows users to edit metadata, change images
    via SteamGridDB, and toggle category assignments.

    Signals:
        category_changed (str, str, bool): Emitted when a category is toggled,
                                           passes (app_id, category, checked).
        edit_metadata (Game): Emitted when the edit button is clicked,
                              passes the current game object.

    Attributes:
        current_game (Game): The currently displayed game.
        name_label (QLabel): Label displaying the game name.
        btn_store (QPushButton): Button to open the Steam store page.
        btn_edit (QPushButton): Button to edit metadata.
        img_grid (ClickableImage): Grid/cover image widget.
        img_hero (ClickableImage): Hero/banner image widget.
        img_logo (ClickableImage): Logo image widget.
        img_icon (ClickableImage): Icon image widget.
        lbl_appid (InfoLabel): Label for app ID.
        lbl_playtime (InfoLabel): Label for playtime.
        lbl_updated (InfoLabel): Label for last update date.
        lbl_proton (QLabel): Label for ProtonDB rating.
        lbl_steam_deck (QLabel): Label for Steam Deck compatibility.
        lbl_reviews (InfoLabel): Label for review score.
        edit_dev (QLineEdit): Read-only field for developer.
        edit_pub (QLineEdit): Read-only field for publisher.
        edit_rel (QLineEdit): Read-only field for release date.
        category_list (HorizontalCategoryList): List of category checkboxes.
    """

    category_changed = pyqtSignal(str, str, bool)
    edit_metadata = pyqtSignal(object)
    pegi_override_requested = pyqtSignal(str, str)  # app_id, rating

    def __init__(self, parent=None):
        """
        Initializes the game details widget.

        Args:
            parent: Parent widget. Defaults to None.
        """
        super().__init__(parent)
        self.current_game = None
        self.current_games = []  # For multi-select mode
        self._create_ui()
        self.clear()

    def _create_ui(self):
        """Creates the user interface for the widget."""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(15, 5, 15, 0)
        main_layout.setSpacing(0)

        # === HEADER (Title & Buttons) ===
        header_layout = QHBoxLayout()

        left_container = QVBoxLayout()
        self.name_label = QLabel(t('ui.game_details.select_placeholder'))
        self.name_label.setFont(QFont("Arial", 22, QFont.Weight.Bold))
        self.name_label.setWordWrap(True)
        self.name_label.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        left_container.addWidget(self.name_label)
        left_container.addStretch()

        # PEGI Rating Box (now on top!)
        self.pegi_image = ClickableImage(self, 128, 128)
        self.pegi_image.set_default_image("resources/images/default_icons.png")
        self.pegi_image.clicked.connect(self._on_pegi_clicked)
        self.pegi_image.right_clicked.connect(self._on_pegi_right_click)  # Connect right click
        self.pegi_image.setStyleSheet(
            "border: 1px solid #FDE100; "
            "background-color: #1b2838;"
        )

        # PEGI layout - centered
        pegi_layout = QHBoxLayout()
        pegi_layout.addWidget(self.pegi_image)
        pegi_layout.addStretch()

        # Buttons layout (below PEGI)
        button_layout = QVBoxLayout()
        button_layout.setSpacing(8)
        button_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)

        self.btn_edit = QPushButton(t('ui.game_details.btn_edit'))
        self.btn_edit.clicked.connect(self._on_edit)
        self.btn_edit.setMinimumWidth(120)

        self.btn_store = QPushButton(t('ui.game_details.btn_store'))
        self.btn_store.clicked.connect(self._open_current_store)
        self.btn_store.setMinimumWidth(120)

        button_layout.addWidget(self.btn_edit)
        button_layout.addWidget(self.btn_store)

        # Combined layout: PEGI on top, buttons below
        buttons_pegi_layout = QVBoxLayout()
        buttons_pegi_layout.setSpacing(12)
        buttons_pegi_layout.addLayout(pegi_layout)
        buttons_pegi_layout.addLayout(button_layout)
        buttons_pegi_layout.addStretch()

        left_container.addLayout(buttons_pegi_layout)

        header_layout.addLayout(left_container, stretch=1)

        # === GALLERY BLOCK ===
        gallery_widget = QWidget()
        gallery_widget.setFixedSize(592, 356)
        gallery_widget.setStyleSheet("background-color: #1a1a1a; border-radius: 4px;")

        gallery_layout = QHBoxLayout(gallery_widget)
        gallery_layout.setContentsMargins(4, 4, 4, 4)
        gallery_layout.setSpacing(4)

        # 1. LEFT: Grid (Cover)
        self.img_grid = ClickableImage(self, 232, 348)
        self.img_grid.set_default_image("resources/images/default_grids.png")
        self.img_grid.clicked.connect(lambda: self._on_image_click('grids'))
        self.img_grid.right_clicked.connect(lambda: self._on_image_right_click('grids'))
        gallery_layout.addWidget(self.img_grid)

        # 2. RIGHT: Stack
        right_stack = QVBoxLayout()
        right_stack.setContentsMargins(0, 0, 0, 0)
        right_stack.setSpacing(4)

        # 2a. Top Right: Logo + Icon
        top_row = QHBoxLayout()
        top_row.setContentsMargins(0, 0, 0, 0)
        top_row.setSpacing(4)

        self.img_logo = ClickableImage(self, 264, 184)
        self.img_logo.set_default_image("resources/images/default_logos.png")
        self.img_logo.clicked.connect(lambda: self._on_image_click('logos'))
        self.img_logo.right_clicked.connect(lambda: self._on_image_right_click('logos'))
        self.img_logo.setStyleSheet("background: transparent;")
        top_row.addWidget(self.img_logo)

        self.img_icon = ClickableImage(self, 80, 80)
        self.img_icon.set_default_image("resources/images/default_icons.png")
        self.img_icon.clicked.connect(lambda: self._on_image_click('icons'))
        self.img_icon.right_clicked.connect(lambda: self._on_image_right_click('icons'))
        self.img_icon.setStyleSheet("background: transparent;")

        icon_container = QVBoxLayout()
        icon_container.setContentsMargins(0, 0, 0, 0)
        icon_container.addWidget(self.img_icon)
        icon_container.addStretch()
        top_row.addLayout(icon_container)

        right_stack.addLayout(top_row)

        # 2b. Bottom Right: Hero
        self.img_hero = ClickableImage(self, 348, 160)
        self.img_hero.set_default_image("resources/images/default_heroes.png")
        self.img_hero.clicked.connect(lambda: self._on_image_click('heroes'))
        self.img_hero.right_clicked.connect(lambda: self._on_image_right_click('heroes'))
        right_stack.addWidget(self.img_hero)

        gallery_layout.addLayout(right_stack)

        header_layout.addWidget(gallery_widget, alignment=Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignRight)
        main_layout.addLayout(header_layout)

        main_layout.addSpacing(20)

        # Separator line
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
        meta_grid.setColumnMinimumWidth(0, 220)
        meta_grid.setColumnMinimumWidth(1, 320)
        meta_grid.setColumnMinimumWidth(2, 340)
        meta_grid.setColumnStretch(3, 1)

        meta_grid.addWidget(QLabel(f"<b>{t('ui.game_details.section_basic')}</b>"), 0, 0)
        self.lbl_appid = InfoLabel('ui.game_details.app_id')
        meta_grid.addWidget(self.lbl_appid, 1, 0)
        self.lbl_playtime = InfoLabel('ui.game_details.playtime')
        meta_grid.addWidget(self.lbl_playtime, 2, 0)
        self.lbl_updated = InfoLabel('ui.game_details.last_update', t('emoji.dash'))
        meta_grid.addWidget(self.lbl_updated, 3, 0)

        meta_grid.addWidget(QLabel(f"<b>{t('ui.game_details.section_ratings')}</b>"), 0, 1)
        self.lbl_proton = QLabel()
        self.lbl_proton.setTextFormat(Qt.TextFormat.RichText)
        self.lbl_proton.setStyleSheet("padding: 1px 0;")
        self._update_proton_label("unknown")
        meta_grid.addWidget(self.lbl_proton, 1, 1)
        self.lbl_steam_deck = QLabel()
        self.lbl_steam_deck.setTextFormat(Qt.TextFormat.RichText)
        self.lbl_steam_deck.setStyleSheet("padding: 1px 0;")
        self._update_steam_deck_label("unknown")
        meta_grid.addWidget(self.lbl_steam_deck, 2, 1)
        self.lbl_reviews = InfoLabel('ui.game_details.reviews', t('emoji.dash'))
        meta_grid.addWidget(self.lbl_reviews, 3, 1)

        meta_grid.addWidget(QLabel(f"<b>{t('ui.game_details.section_metadata')}</b>"), 0, 2)

        def add_meta_field(grid, label_key, row):
            """Helper function to add a metadata field to the grid."""
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
        """
        Updates the ProtonDB rating label with appropriate color and text.

        Args:
            tier (str): The ProtonDB tier (platinum, gold, silver, bronze, native, borked, pending, unknown).
        """
        tier_lower = tier.lower() if tier else "unknown"

        # Valid ProtonDB tiers
        valid_tiers = ["platinum", "gold", "silver", "bronze", "native", "borked", "pending", "unknown"]

        # If tier is not a valid English tier name (e.g. old cached translation), treat as unknown
        if tier_lower not in valid_tiers:
            tier_lower = "unknown"

        colors = {
            "platinum": "#B4C7D9", "gold": "#FDE100", "silver": "#C0C0C0",
            "bronze": "#CD7F32", "native": "#5CB85C", "borked": "#D9534F",
            "pending": "#1C39BB", "unknown": "#FE28A2"
        }
        color = colors.get(tier_lower, "#FE28A2")
        display_text = t(f'ui.game_details.proton_tiers.{tier_lower}')
        if display_text.startswith("["):
            display_text = tier_lower.title()
        title = t('ui.game_details.proton_db')
        self.lbl_proton.setText(
            f"<span style='color:#888;'>{title}:</span> <span style='color:{color}; font-weight:bold;'>{display_text}</span>")

    def _update_steam_deck_label(self, status: str):
        """
        Updates the Steam Deck status label with appropriate color and text.

        Args:
            status (str): The Steam Deck status (verified, playable, unsupported, unknown).
        """
        status_lower = status.lower() if status else "unknown"

        # Valid Steam Deck status values
        valid_statuses = ["verified", "playable", "unsupported", "unknown"]

        # If status is not a valid English status name, treat as unknown
        if status_lower not in valid_statuses:
            status_lower = "unknown"

        colors = {
            "verified": "#59BF40",  # Green - Verified
            "playable": "#FDE100",  # Yellow - Playable
            "unsupported": "#D9534F",  # Red - Unsupported
            "unknown": "#808080"  # Gray - Unknown
        }
        color = colors.get(status_lower, "#808080")
        display_text = t(f'ui.game_details.steam_deck_status.{status_lower}')
        if display_text.startswith("["):
            display_text = status_lower.title()
        title = t('ui.game_details.steam_deck')
        self.lbl_steam_deck.setText(
            f"<span style='color:#888;'>{title}:</span> <span style='color:{color}; font-weight:bold;'>{display_text}</span>")

    def set_games(self, games: List[Game], _all_categories: List[str]):
        """
        Sets multiple games for multi-selection display.

        Shows a summary and allows bulk category operations with tri-state checkboxes.

        Args:
            games (List[Game]): List of selected games.
            _all_categories (List[str]): List of all available categories.
        """
        if not games:
            return

        self.current_game = None  # Clear single game
        self.current_games = games  # Store for multi-select operations

        # Show multi-select summary
        self.name_label.setText(t('ui.game_details.multi_select_title', count=len(games)))
        self.lbl_appid.setText(f"<span style='color:#888;'>{t('ui.game_details.selected')}:</span> <b>{len(games)}</b>")

        # Calculate total playtime
        total_hours = sum(g.playtime_hours for g in games)
        playtime_val = t('ui.game_details.hours', hours=total_hours)
        self.lbl_playtime.setText(
            f"<span style='color:#888;'>{t('ui.game_details.total_playtime')}:</span> <b>{playtime_val}</b>")

        # Clear other fields
        self.lbl_updated.setText(f"<span style='color:#888;'>{t('ui.game_details.last_update')}:</span> <b>-</b>")
        self.lbl_proton.setText(t('ui.game_details.protondb') + ": -")
        self.lbl_steam_deck.setText(t('ui.game_details.steam_deck') + ": -")
        self.lbl_reviews.setText(f"<span style='color:#888;'>{t('ui.game_details.reviews')}:</span> <b>-</b>")
        self.edit_dev.setText("-")
        self.edit_pub.setText("-")
        self.edit_rel.setText("-")

        # Show tri-state checkboxes
        games_categories = [game.categories for game in games]
        self.category_list.set_categories_multi(_all_categories, games_categories)

        # Clear images and show default PEGI
        self.img_grid.clear()
        self.img_hero.clear()
        self.img_logo.clear()
        self.img_icon.clear()

        # Show default icon for PEGI (multi-select has no rating)
        self.pegi_image.load_image(None)  # Shows default image

    def set_game(self, game: Game, _all_categories: List[str]):
        """
        Sets the game to display in the widget.

        This method populates all fields with the game's information and loads
        the game's images.

        Args:
            game (Game): The game to display.
            _all_categories (List[str]): List of all available categories.
        """
        self.current_game = game
        self.current_games = []  # Clear multi-select mode
        self.name_label.setText(game.name)
        self.lbl_appid.setText(f"<span style='color:#888;'>{t('ui.game_details.app_id')}:</span> <b>{game.app_id}</b>")
        playtime_val = t('ui.game_details.hours', hours=game.playtime_hours) if game.playtime_hours > 0 else t(
            'ui.game_details.never_played')
        self.lbl_playtime.setText(
            f"<span style='color:#888;'>{t('ui.game_details.playtime')}:</span> <b>{playtime_val}</b>")
        update_val = format_timestamp_to_date(game.last_updated) if game.last_updated else t('emoji.dash')
        self.lbl_updated.setText(
            f"<span style='color:#888;'>{t('ui.game_details.last_update')}:</span> <b>{update_val}</b>")
        self._update_proton_label(game.proton_db_rating)
        self._update_steam_deck_label(game.steam_deck_status)

        review_val = f"{game.review_score} ({game.review_count})" if game.review_score else t('emoji.dash')
        self.lbl_reviews.setText(
            f"<span style='color:#888;'>{t('ui.game_details.reviews')}:</span> <b>{review_val}</b>")
        unknown = t('ui.game_details.value_unknown')

        # Helper for safe text conversion
        def safe_text(value, formatter=None):
            """Safely converts a value to text with optional formatting."""
            if not value:
                return unknown
            if formatter:
                return formatter(value)
            return str(value)

        # Set fields
        self.edit_dev.setText(safe_text(game.developer))
        self.edit_pub.setText(safe_text(game.publisher))
        self.edit_rel.setText(safe_text(game.release_year, format_timestamp_to_date))
        self.category_list.set_categories(_all_categories, game.categories)

        # Display PEGI rating if available (with ESRB fallback)
        pegi_to_display = ""

        # Check for PEGI first
        if hasattr(game, 'pegi_rating') and game.pegi_rating:
            pegi_to_display = str(game.pegi_rating).strip()
        # Fallback to ESRB if PEGI not available
        elif hasattr(game, 'esrb_rating') and game.esrb_rating:
            esrb = game.esrb_rating
            # ESRB → PEGI mapping
            esrb_to_pegi = {
                'Everyone': '3',
                'Everyone 10+': '7',
                'Teen': '12',
                'Mature': '18',
                'Mature 17+': '18',
                'Adults Only': '18',
                'Adults Only 18+': '18'
            }
            pegi_to_display = esrb_to_pegi.get(esrb, '')

        if pegi_to_display:
            # Try to load PEGI image from /resources/icons/
            pegi_image_path = Path(f"resources/icons/PEGI{pegi_to_display}.png")

            if pegi_image_path.exists():
                self.pegi_image.load_image(str(pegi_image_path))
            else:
                # ClickableImage doesn't support text, show default
                self.pegi_image.load_image(None)

        else:
            # No rating available - show default icon
            self.pegi_image.load_image(None)  # Shows default image

        self._reload_images(game.app_id)

    def _reload_images(self, app_id: str):
        """
        Reloads all game images from the asset manager.

        Args:
            app_id (str): The Steam app ID of the game.
        """
        asset_map = {
            'grids': self.img_grid,
            'heroes': self.img_hero,
            'logos': self.img_logo,
            'icons': self.img_icon
        }
        for asset_type, img_widget in asset_map.items():
            img_widget.load_image(SteamAssets.get_asset_path(app_id, asset_type))

    def clear(self):
        """Clears the widget and resets it to the default state."""
        self.current_game = None
        self.current_games = []
        self.name_label.setText(t('ui.game_details.select_placeholder'))
        self._update_proton_label("unknown")

        self.img_grid.load_image(None)
        self.img_hero.load_image(None)
        self.img_logo.load_image(None)
        self.img_icon.load_image(None)

        # Show default icon for PEGI
        self.pegi_image.load_image(None)  # Shows default image

        self.category_list.set_categories([], [])

    def _on_pegi_clicked(self):
        """Handle PEGI box click - open PEGI selector dialog."""
        if not self.current_game:
            return

        from src.ui.pegi_selector_dialog import PEGISelectorDialog

        # Get current PEGI rating (including override)
        current_rating = getattr(self.current_game, 'pegi_rating', '')

        # Open dialog
        dialog = PEGISelectorDialog(current_rating, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            selected_rating = dialog.get_selected_rating()

            # Emit signal to save override
            self.pegi_override_requested.emit(self.current_game.app_id, selected_rating)

    def _on_pegi_right_click(self):
        """Handle PEGI box right click - show context menu to reset."""
        if not self.current_game:
            return

        menu = QMenu(self)
        # Use existing key or fallback
        reset_text = t('ui.pegi_selector.remove')
        if reset_text.startswith("["):
            reset_text = "Reset Rating"

        reset_action = menu.addAction(reset_text)
        action = menu.exec(QCursor.pos())

        if action == reset_action:
            # Emit signal to remove override (empty string)
            self.pegi_override_requested.emit(self.current_game.app_id, "")

    def _on_category_toggle(self, category_name: str, checked: bool):
        """
        Handles category checkbox toggle events.

        For single game: Emits signal for that game.
        For multi-select: Emits signal for all selected games.

        Args:
            category_name (str): The category name.
            checked (bool): Whether the category checkbox is checked.
        """

        if self.current_game:
            # Single game mode
            self.category_changed.emit(self.current_game.app_id, category_name, checked)
        elif self.current_games:
            # Multi-select mode - emit for all selected games
            for game in self.current_games:
                self.category_changed.emit(game.app_id, category_name, checked)

    def _on_edit(self):
        """Handles the edit button click event."""
        if self.current_game:
            self.edit_metadata.emit(self.current_game)

    def _open_current_store(self):
        """Opens the Steam store page for the current game in the default browser."""
        if self.current_game:
            import webbrowser
            webbrowser.open(f"https://store.steampowered.com/app/{self.current_game.app_id}")

    def _on_image_click(self, img_type: str):
        """
        Handles image click events to open the image selection dialog.

        Args:
            img_type (str): The type of image ('grids', 'heroes', 'logos', 'icons').
        """
        if not self.current_game:
            return
        dialog = ImageSelectionDialog(self, self.current_game.name, self.current_game.app_id, img_type)
        if dialog.exec():
            url = dialog.get_selected_url()
            if url and SteamAssets.save_custom_image(self.current_game.app_id, img_type, url):
                self._reload_single_asset(img_type)

    def _on_image_right_click(self, img_type: str):
        """
        Handles image right-click events to show a context menu.

        Args:
            img_type (str): The type of image ('grids', 'heroes', 'logos', 'icons').
        """
        if not self.current_game:
            return

        menu = QMenu(self)
        reset_action = menu.addAction(t('ui.game_details.gallery.reset'))
        action = menu.exec(QCursor.pos())

        if action == reset_action and SteamAssets.delete_custom_image(self.current_game.app_id, img_type):
            self._reload_single_asset(img_type)

    def _reload_single_asset(self, img_type: str):
        """
        Reloads a single image asset.

        Args:
            img_type (str): The type of image to reload ('grids', 'heroes', 'logos', 'icons').
        """
        asset_map = {
            'grids': self.img_grid,
            'heroes': self.img_hero,
            'logos': self.img_logo,
            'icons': self.img_icon
        }
        if img_type in asset_map:
            path = SteamAssets.get_asset_path(self.current_game.app_id, img_type)
            asset_map[img_type].load_image(path)
