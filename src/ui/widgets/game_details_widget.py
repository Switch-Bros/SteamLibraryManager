# src/ui/widgets/game_details_widget.py

"""Widget for displaying and editing game details.

The heavy UI construction is delegated to
:func:`src.ui.builders.details_ui_builder.build_details_ui`.
This module keeps only the widget class with its signals, data-display
logic, and event handlers.
"""

from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtGui import QCursor
from PyQt6.QtWidgets import (
    QWidget,
    QLabel,
    QLineEdit,
    QPushButton,
    QMenu,
    QDialog,
    QGroupBox,
)

from src.config import config
from src.core.game_manager import Game
from src.core.steam_assets import SteamAssets
from src.ui.builders.details_ui_builder import build_details_ui
from src.ui.dialogs.image_selection_dialog import ImageSelectionDialog
from src.ui.theme import Theme
from src.ui.widgets.category_list import HorizontalCategoryList
from src.ui.widgets.clickable_image import ClickableImage
from src.ui.widgets.info_label import (
    format_proton_html,
    format_deck_html,
    set_info_label_value,
    update_hltb_label,
)
from src.utils.age_ratings import ESRB_TO_PEGI
from src.utils.date_utils import format_timestamp_to_date
from src.utils.i18n import t

__all__ = ["GameDetailsWidget"]


class GameDetailsWidget(QWidget):
    """Widget for displaying and editing detailed game information.

    Signals:
        category_changed: Emitted when a category is toggled (app_id, category, checked).
        edit_metadata: Emitted when the edit button is clicked.
        pegi_override_requested: Emitted when PEGI rating is changed (app_id, rating).
    """

    category_changed = pyqtSignal(str, str, bool)
    edit_metadata = pyqtSignal(object)
    pegi_override_requested = pyqtSignal(str, str)

    # UI components — populated by build_details_ui()
    name_label: QLabel
    btn_edit: QPushButton
    btn_store: QPushButton
    pegi_image: ClickableImage
    img_grid: ClickableImage
    img_hero: ClickableImage
    img_logo: ClickableImage
    img_icon: ClickableImage
    lbl_appid: QLabel
    lbl_playtime: QLabel
    lbl_updated: QLabel
    lbl_proton: QLabel
    lbl_steam_deck: QLabel
    lbl_reviews: QLabel
    edit_dev: QLineEdit
    edit_pub: QLineEdit
    edit_rel: QLineEdit
    lbl_hltb_main: QLabel
    lbl_hltb_extras: QLabel
    lbl_hltb_comp: QLabel
    lbl_hltb_all: QLabel
    lbl_achievement_total: QLabel
    lbl_achievement_progress: QLabel
    lbl_achievement_perfect: QLabel
    lbl_curator_overlap: QLabel
    lbl_description: QLabel
    lbl_private_badge: QLabel
    dlc_group: QGroupBox
    dlc_content: QLabel
    category_list: HorizontalCategoryList

    def __init__(self, parent=None):
        """Initializes the game details widget.

        Args:
            parent: Parent widget.
        """
        super().__init__(parent)
        self.current_game: Game | None = None
        self.current_games: list[Game] = []
        build_details_ui(self)
        self.clear()

    # ------------------------------------------------------------------
    # Rating label helpers
    # ------------------------------------------------------------------

    def _update_proton_label(self, tier: str) -> None:
        """Updates the ProtonDB label with tier-colored HTML."""
        self.lbl_proton.setText(format_proton_html(tier))

    def _update_steam_deck_label(self, status: str) -> None:
        """Updates the Steam Deck label with status-colored HTML."""
        self.lbl_steam_deck.setText(format_deck_html(status))

    # ------------------------------------------------------------------
    # Data display
    # ------------------------------------------------------------------

    def set_games(self, games: list[Game], _all_categories: list[str]) -> None:
        """Sets multiple games for multi-selection display.

        Args:
            games: List of selected games.
            _all_categories: All available categories.
        """
        if not games:
            return

        self.current_game = None
        self.current_games = games

        self.name_label.setText(t("ui.game_details.multi_select_title", count=len(games)))
        self.lbl_appid.setText(
            f"<span style='color:{Theme.TEXT_MUTED};'>{t('ui.game_details.selected')}:</span> <b>{len(games)}</b>"
        )

        total_hours = sum(g.playtime_hours for g in games)
        playtime_val = t("ui.game_details.hours", hours=total_hours)
        self.lbl_playtime.setText(
            f"<span style='color:{Theme.TEXT_MUTED};'>"
            f"{t('ui.game_details.total_playtime')}:</span> <b>{playtime_val}</b>"
        )

        self.lbl_updated.setText(
            f"<span style='color:{Theme.TEXT_MUTED};'>{t('ui.game_details.last_update')}:</span> <b>-</b>"
        )
        self.lbl_proton.setText(t("ui.game_details.protondb") + ": -")
        self.lbl_steam_deck.setText(t("ui.game_details.steam_deck") + ": -")
        self.lbl_reviews.setText(
            f"<span style='color:{Theme.TEXT_MUTED};'>{t('ui.game_details.reviews')}:</span> <b>-</b>"
        )
        self.edit_dev.setText(t("emoji.dash"))
        self.edit_pub.setText(t("emoji.dash"))
        self.edit_rel.setText(t("emoji.dash"))

        dash = t("emoji.dash")
        update_hltb_label(self.lbl_hltb_main, 0, dash)
        update_hltb_label(self.lbl_hltb_extras, 0, dash)
        update_hltb_label(self.lbl_hltb_comp, 0, dash)
        update_hltb_label(self.lbl_hltb_all, 0, dash)
        self._clear_achievement_labels()

        games_categories = [game.categories for game in games]
        self.category_list.set_categories_multi(_all_categories, games_categories)

        self.lbl_description.hide()
        self.lbl_private_badge.hide()
        self.dlc_group.hide()

        self.img_grid.clear()
        self.img_hero.clear()
        self.img_logo.clear()
        self.img_icon.clear()
        self.pegi_image.load_image(None)

    def set_game(self, game: Game, _all_categories: list[str]) -> None:
        """Sets the game to display in the widget.

        Args:
            game: The game to display.
            _all_categories: All available categories.
        """
        self.current_game = game
        self.current_games = []
        self.name_label.setText(game.name)
        self.lbl_appid.setText(
            f"<span style='color:{Theme.TEXT_MUTED};'>{t('ui.game_details.app_id')}:</span> <b>{game.app_id}</b>"
        )
        playtime_val = (
            t("ui.game_details.hours", hours=game.playtime_hours)
            if game.playtime_hours > 0
            else t("ui.game_details.never_played")
        )
        self.lbl_playtime.setText(
            f"<span style='color:{Theme.TEXT_MUTED};'>{t('ui.game_details.playtime')}:</span> <b>{playtime_val}</b>"
        )
        update_val = format_timestamp_to_date(game.last_updated) if game.last_updated else t("emoji.dash")
        self.lbl_updated.setText(
            f"<span style='color:{Theme.TEXT_MUTED};'>{t('ui.game_details.last_update')}:</span> <b>{update_val}</b>"
        )
        self._update_proton_label(game.proton_db_rating)
        self._update_steam_deck_label(game.steam_deck_status)

        # Reviews
        if game.review_score:
            if game.review_percentage > 0:
                review_val = (
                    f"{game.review_percentage}{t('emoji.percent')} | " f"{game.review_score} ({game.review_count})"
                )
            else:
                review_val = f"{game.review_score} ({game.review_count})"
        else:
            review_val = t("emoji.dash")

        self.lbl_reviews.setText(
            f"<span style='color:{Theme.TEXT_MUTED};'>{t('ui.game_details.reviews')}:</span> <b>{review_val}</b>"
        )

        # Curator overlap
        curator_val = game.curator_overlap if game.curator_overlap else t("emoji.dash")
        set_info_label_value(self.lbl_curator_overlap, curator_val)

        unknown = t("ui.game_details.value_unknown")

        def safe_text(value, formatter=None):
            """Safely converts a value to text with optional formatting."""
            if not value:
                return unknown
            return formatter(value) if formatter else str(value)

        self.edit_dev.setText(safe_text(game.developer))
        self.edit_dev.setCursorPosition(0)
        self.edit_pub.setText(safe_text(game.publisher))
        self.edit_pub.setCursorPosition(0)
        self.edit_rel.setText(safe_text(game.release_year, format_timestamp_to_date))
        self.edit_rel.setCursorPosition(0)

        # HLTB data
        dash = t("emoji.dash")
        update_hltb_label(self.lbl_hltb_main, game.hltb_main_story, dash)
        update_hltb_label(self.lbl_hltb_extras, game.hltb_main_extras, dash)
        update_hltb_label(self.lbl_hltb_comp, game.hltb_completionist, dash)
        all_vals = [v for v in (game.hltb_main_story, game.hltb_main_extras, game.hltb_completionist) if v > 0]
        all_avg = sum(all_vals) / len(all_vals) if all_vals else 0.0
        update_hltb_label(self.lbl_hltb_all, all_avg, dash)

        # Achievement data
        self._update_achievement_labels(game)

        self.category_list.set_categories(_all_categories, game.categories)

        # Description
        if game.description:
            self.lbl_description.setText(game.description[:300])
            self.lbl_description.show()
        else:
            self.lbl_description.hide()

        # Private badge
        if game.is_private:
            self.lbl_private_badge.setText(t("ui.detail.private_app"))
            self.lbl_private_badge.show()
        else:
            self.lbl_private_badge.hide()

        # DLC section
        if game.dlc_ids:
            self.dlc_group.setTitle(t("ui.detail.dlc_label") + f" ({len(game.dlc_ids)})")
            self.dlc_content.setText(", ".join(str(d) for d in game.dlc_ids))
            self.dlc_group.show()
        else:
            self.dlc_group.hide()

        # PEGI rating
        self._load_pegi_rating(game)

        self._reload_images(game.app_id)

    # ------------------------------------------------------------------
    # Achievement helpers
    # ------------------------------------------------------------------

    def _update_achievement_labels(self, game: Game) -> None:
        """Updates achievement total, progress and perfect labels.

        Args:
            game: The game whose achievement data to display.
        """
        _GOLD = Theme.ACHIEVEMENT_GOLD

        if game.achievement_total > 0:
            set_info_label_value(self.lbl_achievement_total, str(game.achievement_total))

            progress_text = t(
                "ui.game_details.achievement_format",
                unlocked=game.achievement_unlocked,
                total=game.achievement_total,
                percentage=f"{game.achievement_percentage:.0f}",
            )

            if game.achievement_perfect:
                set_info_label_value(self.lbl_achievement_progress, progress_text, color=_GOLD)
                set_info_label_value(self.lbl_achievement_total, str(game.achievement_total), color=_GOLD)
                trophy = t("emoji.trophy")
                perfect_text = t("ui.game_details.achievement_perfect")
                self.lbl_achievement_perfect.setText(
                    f"<span style='color:{_GOLD}; font-weight:bold;'>{trophy} {perfect_text}</span>"
                )
            else:
                set_info_label_value(self.lbl_achievement_progress, progress_text)
                self.lbl_achievement_perfect.setText("")
        else:
            no_ach = t("ui.game_details.achievement_none")
            set_info_label_value(self.lbl_achievement_total, t("emoji.dash"))
            set_info_label_value(self.lbl_achievement_progress, no_ach)
            self.lbl_achievement_perfect.setText("")

    def _clear_achievement_labels(self) -> None:
        """Resets achievement labels to their default empty state."""
        dash = t("emoji.dash")
        set_info_label_value(self.lbl_achievement_total, dash)
        set_info_label_value(self.lbl_achievement_progress, dash)
        self.lbl_achievement_perfect.setText("")

    # ------------------------------------------------------------------
    # Image handling
    # ------------------------------------------------------------------

    @property
    def _asset_map(self) -> dict[str, ClickableImage]:
        """Maps asset type names to their corresponding image widgets."""
        return {"grids": self.img_grid, "heroes": self.img_hero, "logos": self.img_logo, "icons": self.img_icon}

    def _reload_images(self, app_id: str) -> None:
        """Reloads all game images from the asset manager.

        Args:
            app_id: The Steam app ID.
        """
        for asset_type, img_widget in self._asset_map.items():
            img_widget.load_image(SteamAssets.get_asset_path(app_id, asset_type))

    def _reload_single_asset(self, img_type: str) -> None:
        """Reloads a single image asset after change.

        Args:
            img_type: Image type ('grids', 'heroes', 'logos', 'icons').
        """
        if not self.current_game:
            return
        widget = self._asset_map.get(img_type)
        if widget:
            widget.load_image(SteamAssets.get_asset_path(self.current_game.app_id, img_type))

    def on_image_click(self, img_type: str) -> None:
        """Opens the image selection dialog on click.

        Args:
            img_type: Image type ('grids', 'heroes', 'logos', 'icons').
        """
        if not self.current_game:
            return
        dialog = ImageSelectionDialog(self, self.current_game.name, int(self.current_game.app_id), img_type)
        if dialog.exec():
            url = dialog.get_selected_url()
            if url and SteamAssets.save_custom_image(self.current_game.app_id, img_type, url):
                self._reload_single_asset(img_type)

    def on_image_right_click(self, img_type: str) -> None:
        """Shows reset context menu on right-click.

        Args:
            img_type: Image type ('grids', 'heroes', 'logos', 'icons').
        """
        if not self.current_game:
            return
        menu = QMenu(self)
        reset_action = menu.addAction(t("ui.game_details.gallery.reset"))
        action = menu.exec(QCursor.pos())
        if action == reset_action and SteamAssets.delete_custom_image(self.current_game.app_id, img_type):
            self._reload_single_asset(img_type)

    # ------------------------------------------------------------------
    # PEGI handling
    # ------------------------------------------------------------------

    def _load_pegi_rating(self, game: Game) -> None:
        """Loads and displays the PEGI rating for a game.

        Tries PEGI field first, falls back to ESRB mapping, then Steam Store fetch.

        Args:
            game: The game to load PEGI for.
        """
        pegi_to_display = ""

        if hasattr(game, "pegi_rating") and game.pegi_rating:
            pegi_to_display = str(game.pegi_rating).strip()
        elif hasattr(game, "esrb_rating") and game.esrb_rating:
            pegi_to_display = ESRB_TO_PEGI.get(game.esrb_rating.lower(), "")

        if not pegi_to_display:
            from src.integrations.steam_store import SteamStoreScraper

            scraper = SteamStoreScraper(Path.home() / ".steam_library_manager" / "cache", "en")
            fetched_pegi = scraper.fetch_age_rating(game.app_id)
            if fetched_pegi:
                pegi_to_display = fetched_pegi
                game.pegi_rating = fetched_pegi

        if pegi_to_display:
            pegi_path = config.ICONS_DIR / f"PEGI{pegi_to_display}.png"
            self.pegi_image.load_image(str(pegi_path) if pegi_path.exists() else None)
        else:
            self.pegi_image.load_image(None)

    def on_pegi_clicked(self) -> None:
        """Opens the PEGI selector dialog on click."""
        if not self.current_game:
            return
        from src.ui.dialogs.pegi_selector_dialog import PEGISelectorDialog

        current_rating = getattr(self.current_game, "pegi_rating", "")
        dialog = PEGISelectorDialog(current_rating, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            selected_rating = dialog.get_selected_rating()
            self.pegi_override_requested.emit(self.current_game.app_id, selected_rating)

    def on_pegi_right_click(self) -> None:
        """Shows reset context menu on PEGI right-click."""
        if not self.current_game:
            return
        menu = QMenu(self)
        reset_text = t("ui.pegi_selector.remove")
        if reset_text.startswith("["):
            reset_text = "Reset Rating"
        reset_action = menu.addAction(reset_text)
        action = menu.exec(QCursor.pos())
        if action == reset_action:
            self.pegi_override_requested.emit(self.current_game.app_id, "")

    # ------------------------------------------------------------------
    # Clear / Reset
    # ------------------------------------------------------------------

    def clear(self) -> None:
        """Reset all displayed game details to their default empty state."""
        self.current_game = None
        self.current_games = []
        self.name_label.setText(t("ui.game_details.select_placeholder"))
        self._update_proton_label("unknown")
        self._update_steam_deck_label("unknown")
        self._clear_achievement_labels()
        self.lbl_description.hide()
        self.lbl_private_badge.hide()
        self.dlc_group.hide()

        self.img_grid.load_image(None)
        self.img_hero.load_image(None)
        self.img_logo.load_image(None)
        self.img_icon.load_image(None)
        self.pegi_image.load_image(None)

        self.category_list.set_categories([], [])

    # ------------------------------------------------------------------
    # Event handlers
    # ------------------------------------------------------------------

    def on_category_toggle(self, category_name: str, checked: bool) -> None:
        """Handles category checkbox toggle events.

        Args:
            category_name: The category name.
            checked: Whether the checkbox is checked.
        """
        if self.current_game:
            self.category_changed.emit(self.current_game.app_id, category_name, checked)
        elif self.current_games:
            for game in self.current_games:
                self.category_changed.emit(game.app_id, category_name, checked)

    def on_edit(self) -> None:
        """Opens the metadata editor for the current game."""
        if self.current_game:
            self.edit_metadata.emit(self.current_game)

    def open_current_store(self) -> None:
        """Opens the Steam Store page in the default browser."""
        if self.current_game:
            from src.utils.open_url import open_url

            open_url(f"https://store.steampowered.com/app/{self.current_game.app_id}")
