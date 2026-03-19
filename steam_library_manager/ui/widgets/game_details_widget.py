#
# steam_library_manager/ui/widgets/game_details_widget.py
# Widget for displaying and editing game details
#
# Copyright (c) 2025-2026 SwitchBros
# Licensed under the MIT License. See LICENSE for details.
#

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

from steam_library_manager.config import config
from steam_library_manager.core.steam_assets import SteamAssets
from steam_library_manager.ui.builders.details_ui_builder import (
    build_details_ui,
    rescale_ui,
    _calc_scale,
    _detect_initial_scale,
)
from steam_library_manager.ui.dialogs.image_selection_dialog import ImageSelectionDialog
from steam_library_manager.ui.theme import Theme
from steam_library_manager.ui.widgets.category_list import HorizontalCategoryList
from steam_library_manager.ui.widgets.clickable_image import ClickableImage
from steam_library_manager.ui.widgets.info_label import (
    format_proton_html,
    format_deck_html,
    set_info_label_value,
    update_hltb_label,
)
from steam_library_manager.utils.age_ratings import ESRB_TO_PEGI
from steam_library_manager.utils.date_utils import format_timestamp_to_date
from steam_library_manager.utils.i18n import t

__all__ = ["GameDetailsWidget"]


class GameDetailsWidget(QWidget):
    """Game detail panel showing metadata, images, categories, and
    achievements. Handles single and multi-game selections."""

    category_changed = pyqtSignal(str, str, bool)
    edit_metadata = pyqtSignal(object)
    pegi_override_requested = pyqtSignal(str, str)

    # UI components - populated by build_details_ui()
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
        super().__init__(parent)
        self.current_game = None
        self.current_games = []
        self._ui_scale = 1.0
        self._initial_scale_applied = False
        build_details_ui(self)
        self.clear()

    def showEvent(self, event):
        # apply screen-based scaling on first show
        super().showEvent(event)
        if not self._initial_scale_applied:
            self._initial_scale_applied = True
            import logging

            scale = _detect_initial_scale()
            log = logging.getLogger("steamlibmgr.details_ui")
            log.info("showEvent: initial scale=%.3f (current=%.3f)", scale, self._ui_scale)
            if abs(scale - self._ui_scale) > 0.01:
                self._ui_scale = scale
                rescale_ui(self, scale)

    def resizeEvent(self, event):
        # recalc scale on resize; small screens keep initial scale
        super().resizeEvent(event)
        if self._initial_scale_applied and self._ui_scale < 1.0:
            return
        w = event.size().width()
        new_scale = _calc_scale(w)
        if abs(new_scale - self._ui_scale) > 0.01:
            self._ui_scale = new_scale
            rescale_ui(self, new_scale)

    # -- rating label helpers --

    def _update_proton_label(self, tier):
        self.lbl_proton.setText(format_proton_html(tier))

    def _update_steam_deck_label(self, status):
        self.lbl_steam_deck.setText(format_deck_html(status))

    # -- data display --

    def set_games(self, games, _all_categories):
        # display summary for multi-game selection
        if not games:
            return

        self.current_game = None
        self.current_games = games

        self.name_label.setText(t("ui.game_details.multi_select_title", count=len(games)))
        self.lbl_appid.setText(
            "<span style='color:%s;'>%s:</span> <b>%d</b>"
            % (Theme.TXT_MUTED, t("ui.game_details.selected"), len(games))
        )

        hrs = sum(g.playtime_hours for g in games)
        pt_val = t("ui.game_details.hours", hours=hrs)
        self.lbl_playtime.setText(
            "<span style='color:%s;'>%s:</span> <b>%s</b>"
            % (Theme.TXT_MUTED, t("ui.game_details.total_playtime"), pt_val)
        )

        self.lbl_updated.setText(
            "<span style='color:%s;'>%s:</span> <b>-</b>" % (Theme.TXT_MUTED, t("ui.game_details.last_update"))
        )
        self.lbl_proton.setText(t("ui.game_details.protondb") + ": -")
        self.lbl_steam_deck.setText(t("ui.game_details.steam_deck") + ": -")
        self.lbl_reviews.setText(
            "<span style='color:%s;'>%s:</span> <b>-</b>" % (Theme.TXT_MUTED, t("ui.game_details.reviews"))
        )
        self.edit_dev.setText(t("emoji.dash"))
        self.edit_pub.setText(t("emoji.dash"))
        self.edit_rel.setText(t("emoji.dash"))

        dash = t("emoji.dash")
        update_hltb_label(self.lbl_hltb_main, 0, dash)
        update_hltb_label(self.lbl_hltb_extras, 0, dash)
        update_hltb_label(self.lbl_hltb_comp, 0, dash)
        update_hltb_label(self.lbl_hltb_all, 0, dash)
        self._clear_ach()

        cats = [game.categories for game in games]
        self.category_list.set_categories_multi(_all_categories, cats)

        self.lbl_description.hide()
        self.lbl_private_badge.hide()
        self.dlc_group.hide()

        self.img_grid.clear()
        self.img_hero.clear()
        self.img_logo.clear()
        self.img_icon.clear()
        self.pegi_image.load_image(None)

    def set_game(self, game, _all_categories):
        # display details for a single game
        self.current_game = game
        self.current_games = []
        self.name_label.setText(game.name)
        self.lbl_appid.setText(
            "<span style='color:%s;'>%s:</span> <b>%s</b>" % (Theme.TXT_MUTED, t("ui.game_details.app_id"), game.app_id)
        )
        pt_val = (
            t("ui.game_details.hours", hours=game.playtime_hours)
            if game.playtime_hours > 0
            else t("ui.game_details.never_played")
        )
        self.lbl_playtime.setText(
            "<span style='color:%s;'>%s:</span> <b>%s</b>" % (Theme.TXT_MUTED, t("ui.game_details.playtime"), pt_val)
        )
        upd = format_timestamp_to_date(game.last_updated) if game.last_updated else t("emoji.dash")
        self.lbl_updated.setText(
            "<span style='color:%s;'>%s:</span> <b>%s</b>" % (Theme.TXT_MUTED, t("ui.game_details.last_update"), upd)
        )
        self._update_proton_label(game.proton_db_rating)
        self._update_steam_deck_label(game.steam_deck_status)

        # reviews
        if game.review_score:
            if game.review_percentage > 0:
                rv = "%s%s | %s (%s)" % (
                    game.review_percentage,
                    t("emoji.percent"),
                    game.review_score,
                    game.review_count,
                )
            else:
                rv = "%s (%s)" % (game.review_score, game.review_count)
        else:
            rv = t("emoji.dash")

        self.lbl_reviews.setText(
            "<span style='color:%s;'>%s:</span> <b>%s</b>" % (Theme.TXT_MUTED, t("ui.game_details.reviews"), rv)
        )

        # curator overlap
        cur = game.curator_overlap if game.curator_overlap else t("emoji.dash")
        set_info_label_value(self.lbl_curator_overlap, cur)

        unknown = t("ui.game_details.value_unknown")

        def safe(val, fmt=None):
            if not val:
                return unknown
            return fmt(val) if fmt else str(val)

        self.edit_dev.setText(safe(game.developer))
        self.edit_dev.setCursorPosition(0)
        self.edit_pub.setText(safe(game.publisher))
        self.edit_pub.setCursorPosition(0)
        self.edit_rel.setText(safe(game.release_year, format_timestamp_to_date))
        self.edit_rel.setCursorPosition(0)

        # HLTB
        dash = t("emoji.dash")
        update_hltb_label(self.lbl_hltb_main, game.hltb_main_story, dash)
        update_hltb_label(self.lbl_hltb_extras, game.hltb_main_extras, dash)
        update_hltb_label(self.lbl_hltb_comp, game.hltb_completionist, dash)
        vals = [v for v in (game.hltb_main_story, game.hltb_main_extras, game.hltb_completionist) if v > 0]
        avg = sum(vals) / len(vals) if vals else 0.0
        update_hltb_label(self.lbl_hltb_all, avg, dash)

        self._set_ach(game)
        self.category_list.set_categories(_all_categories, game.categories)

        # description
        if game.description:
            self.lbl_description.setText(game.description[:300])
            self.lbl_description.show()
        else:
            self.lbl_description.hide()

        # private badge
        if game.is_private:
            self.lbl_private_badge.setText(t("ui.detail.private_app"))
            self.lbl_private_badge.show()
        else:
            self.lbl_private_badge.hide()

        # DLC section
        if game.dlc_ids:
            self.dlc_group.setTitle(t("ui.detail.dlc_label") + " (%d)" % len(game.dlc_ids))
            self.dlc_content.setText(", ".join(str(d) for d in game.dlc_ids))
            self.dlc_group.show()
        else:
            self.dlc_group.hide()

        self._show_pegi(game)
        self._load_imgs(game.app_id)

    # -- achievement helpers --

    def _set_ach(self, game):
        # update achievement total, progress, perfect labels
        gold = Theme.ACHV_GOLD

        if game.achievement_total > 0:
            set_info_label_value(self.lbl_achievement_total, str(game.achievement_total))

            prog = t(
                "ui.game_details.achievement_format",
                unlocked=game.achievement_unlocked,
                total=game.achievement_total,
                percentage="%.0f" % game.achievement_percentage,
            )

            if game.achievement_perfect:
                set_info_label_value(self.lbl_achievement_progress, prog, color=gold)
                set_info_label_value(self.lbl_achievement_total, str(game.achievement_total), color=gold)
                trophy = t("emoji.trophy")
                perf = t("ui.game_details.achievement_perfect")
                self.lbl_achievement_perfect.setText(
                    "<span style='color:%s; font-weight:bold;'>%s %s</span>" % (gold, trophy, perf)
                )
            else:
                set_info_label_value(self.lbl_achievement_progress, prog)
                self.lbl_achievement_perfect.setText("")
        else:
            no_ach = t("ui.game_details.achievement_none")
            set_info_label_value(self.lbl_achievement_total, t("emoji.dash"))
            set_info_label_value(self.lbl_achievement_progress, no_ach)
            self.lbl_achievement_perfect.setText("")

    def _clear_ach(self):
        dash = t("emoji.dash")
        set_info_label_value(self.lbl_achievement_total, dash)
        set_info_label_value(self.lbl_achievement_progress, dash)
        self.lbl_achievement_perfect.setText("")

    # -- image handling --

    @property
    def _assets(self):
        return {"grids": self.img_grid, "heroes": self.img_hero, "logos": self.img_logo, "icons": self.img_icon}

    def _load_imgs(self, app_id):
        for atype, widget in self._assets.items():
            path = SteamAssets.get_asset_path(app_id, atype)
            fb = SteamAssets.get_cdn_fallback_urls(app_id, atype) if path.startswith("http") else None
            widget.load_image(path, fallback_urls=fb)

    def _reload_one(self, img_type):
        if not self.current_game:
            return
        widget = self._assets.get(img_type)
        if widget:
            aid = self.current_game.app_id
            path = SteamAssets.get_asset_path(aid, img_type)
            fb = SteamAssets.get_cdn_fallback_urls(aid, img_type) if path.startswith("http") else None
            widget.load_image(path, fallback_urls=fb)

    def on_image_click(self, img_type):
        # opens the image selection dialog
        if not self.current_game:
            return
        dlg = ImageSelectionDialog(self, self.current_game.name, int(self.current_game.app_id), img_type)
        if dlg.exec():
            url = dlg.get_selected_url()
            if url and SteamAssets.save_custom_image(self.current_game.app_id, img_type, url):
                self._reload_one(img_type)

    def on_image_right_click(self, img_type):
        # reset context menu on right-click
        if not self.current_game:
            return
        menu = QMenu(self)
        reset_act = menu.addAction(t("ui.game_details.gallery.reset"))
        action = menu.exec(QCursor.pos())
        if action == reset_act and SteamAssets.delete_custom_image(self.current_game.app_id, img_type):
            self._reload_one(img_type)

    # -- PEGI handling --

    def _show_pegi(self, game):
        # loads PEGI rating: tries pegi_rating, then ESRB mapping, then store fetch
        rating = ""

        if hasattr(game, "pegi_rating") and game.pegi_rating:
            rating = str(game.pegi_rating).strip()
        elif hasattr(game, "esrb_rating") and game.esrb_rating:
            rating = ESRB_TO_PEGI.get(game.esrb_rating.lower(), "")

        if not rating:
            from steam_library_manager.integrations.steam_store import SteamStoreScraper

            scraper = SteamStoreScraper(Path.home() / ".steam_library_manager" / "cache", "en")
            fetched = scraper.fetch_age_rating(game.app_id)
            if fetched:
                rating = fetched
                game.pegi_rating = fetched

        if rating:
            pegi_path = config.ICONS_DIR / ("PEGI%s.webp" % rating)
            self.pegi_image.load_image(str(pegi_path) if pegi_path.exists() else None)
        else:
            self.pegi_image.load_image(None)

    def on_pegi_clicked(self):
        # opens the PEGI selector dialog
        if not self.current_game:
            return
        from steam_library_manager.ui.dialogs.pegi_selector_dialog import PEGISelectorDialog

        cur = getattr(self.current_game, "pegi_rating", "")
        dlg = PEGISelectorDialog(cur, self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            sel = dlg.get_selected_rating()
            self.pegi_override_requested.emit(self.current_game.app_id, sel)

    def on_pegi_right_click(self):
        # reset context menu on PEGI right-click
        if not self.current_game:
            return
        menu = QMenu(self)
        txt = t("ui.pegi_selector.remove")
        if txt.startswith("["):
            txt = "Reset Rating"
        reset_act = menu.addAction(txt)
        action = menu.exec(QCursor.pos())
        if action == reset_act:
            self.pegi_override_requested.emit(self.current_game.app_id, "")

    # -- clear / reset --

    def clear(self):
        # reset all displayed game details to default empty state
        self.current_game = None
        self.current_games = []
        self.name_label.setText(t("ui.game_details.select_placeholder"))
        self._update_proton_label("unknown")
        self._update_steam_deck_label("unknown")
        self._clear_ach()
        self.lbl_description.hide()
        self.lbl_private_badge.hide()
        self.dlc_group.hide()

        self.img_grid.load_image(None)
        self.img_hero.load_image(None)
        self.img_logo.load_image(None)
        self.img_icon.load_image(None)
        self.pegi_image.load_image(None)

        self.category_list.set_categories([], [])

    # -- event handlers --

    def on_category_toggle(self, category_name, checked):
        if self.current_game:
            self.category_changed.emit(self.current_game.app_id, category_name, checked)
        elif self.current_games:
            for game in self.current_games:
                self.category_changed.emit(game.app_id, category_name, checked)

    def on_edit(self):
        if self.current_game:
            self.edit_metadata.emit(self.current_game)

    def open_current_store(self):
        # opens the Steam Store page in the browser
        if self.current_game:
            from steam_library_manager.utils.open_url import open_url

            open_url("https://store.steampowered.com/app/%s" % self.current_game.app_id)
