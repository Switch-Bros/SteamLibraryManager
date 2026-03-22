#
# steam_library_manager/ui/actions/edit_actions.py
# UI action handlers for edit menu operations
#
# Copyright © 2025-2026 SwitchBros
# Licensed under the MIT License. See LICENSE for details.
#
# FIXME: _do_auto_categorize is too long

from __future__ import annotations

__all__ = ["EditActions"]

from typing import TYPE_CHECKING

from PyQt6.QtWidgets import QMessageBox

from steam_library_manager.core.game_manager import Game
from steam_library_manager.ui.dialogs.auto_categorize_dialog import AutoCategorizeDialog
from steam_library_manager.ui.widgets.ui_helper import UIHelper
from steam_library_manager.utils.i18n import t

if TYPE_CHECKING:
    from steam_library_manager.ui.main_window import MainWindow


class EditActions:
    """Auto-categorization and Smart Collection actions."""

    def __init__(self, main_window: "MainWindow") -> None:
        self.mw = main_window
        self.dialog_games = []

    # auto-categorization

    def auto_categorize(self) -> None:
        if self.mw.selected_games:
            self._show_auto_categorize_dialog(self.mw.selected_games, None)
        elif self.mw.game_manager:
            self._show_auto_categorize_dialog(self.mw.game_manager.get_uncategorized_games(), None)

    def auto_categorize_selected(self) -> None:
        if self.mw.selected_games:
            self._show_auto_categorize_dialog(self.mw.selected_games, None)

    def auto_categorize_single(self, game: Game) -> None:
        self._show_auto_categorize_dialog([game], None)

    def auto_categorize_category(self, category: str) -> None:
        if not self.mw.game_manager:
            return

        if category == t("categories.all_games"):
            self._show_auto_categorize_dialog(self.mw.game_manager.get_real_games(), category)
        elif category == t("categories.uncategorized"):
            self._show_auto_categorize_dialog(self.mw.game_manager.get_uncategorized_games(), category)
        else:
            self._show_auto_categorize_dialog(self.mw.game_manager.get_games_by_category(category), category)

    def _show_auto_categorize_dialog(self, games: list[Game], category_name: str | None) -> None:
        self.dialog_games = games
        if not self.mw.game_manager:
            return

        dialog = AutoCategorizeDialog(
            self.mw,
            games,
            len(self.mw.game_manager.games),
            lambda settings: self._check_and_start(settings, dialog),
            category_name,
        )
        dialog.exec()

    # check tag coverage before starting
    def _check_and_start(self, settings: dict, dialog: "AutoCategorizeDialog") -> None:
        if "tags" not in settings.get("methods", []):
            dialog.accept()
            self._do_auto_categorize(settings)
            return

        if not self.mw.steam_scraper or not self.mw.game_manager or not self.mw.autocategorize_service:
            dialog.accept()
            self._do_auto_categorize(settings)
            return

        # Determine scope
        if settings["scope"] == "all":
            games_to_use = self.mw.game_manager.get_library_entries()
        else:
            games_to_use = self.dialog_games

        # Check tag coverage from DB (not file cache)
        db_path = self._get_db_path()
        if db_path:
            from steam_library_manager.core.database import Database

            temp_db = Database(db_path)
            try:
                cov = self.mw.autocategorize_service.get_tag_coverage_from_db(len(games_to_use), temp_db)
            finally:
                temp_db.close()
        else:
            cov = self.mw.autocategorize_service.get_tag_coverage_from_db(len(games_to_use))

        if cov["percentage"] >= 50:
            dialog.accept()
            self._do_auto_categorize(settings)
            return

        # Show warning with custom buttons
        missing = cov["missing"]
        eta = self.mw.autocategorize_service.estimate_time(missing)

        msg = QMessageBox(self.mw)
        msg.setIcon(QMessageBox.Icon.Warning)
        msg.setWindowTitle(t("auto_categorize.cache_warning_title"))
        msg.setText(
            t(
                "auto_categorize.cache_warning_message",
                cached=cov["cached"],
                total=cov["total"],
                time=eta,
            )
        )

        # Manual buttons, no StandardButtons
        yes_btn = msg.addButton(t("common.yes"), QMessageBox.ButtonRole.YesRole)
        no_btn = msg.addButton(t("common.no"), QMessageBox.ButtonRole.NoRole)
        msg.setDefaultButton(no_btn)

        msg.exec()

        if msg.clickedButton() == yes_btn:
            dialog.accept()
            self._do_auto_categorize(settings)

    # run auto-categorization methods
    def _do_auto_categorize(self, settings: dict) -> None:
        # noinspection PyProtectedMember
        parser = self.mw._get_active_parser()
        if not settings or not parser or not self.mw.autocategorize_service:
            return

        games = self.mw.game_manager.get_library_entries() if settings["scope"] == "all" else self.dialog_games
        methods = settings["methods"]

        progress = UIHelper.create_progress_dialog(
            self.mw,
            t("auto_categorize.processing", current=0, total=len(games)),
            maximum=len(methods) * len(games),
        )

        step = 0

        methods_map = {
            "publisher": self.mw.autocategorize_service.categorize_by_publisher,
            "franchise": self.mw.autocategorize_service.categorize_by_franchise,
            "genre": self.mw.autocategorize_service.categorize_by_genre,
            "developer": self.mw.autocategorize_service.categorize_by_developer,
            "platform": self.mw.autocategorize_service.categorize_by_platform,
            "user_score": self.mw.autocategorize_service.categorize_by_user_score,
            "hours_played": self.mw.autocategorize_service.categorize_by_hours_played,
            "flags": self.mw.autocategorize_service.categorize_by_flags,
            "vr": self.mw.autocategorize_service.categorize_by_vr,
            "year": self.mw.autocategorize_service.categorize_by_year,
            "hltb": self.mw.autocategorize_service.categorize_by_hltb,
            "language": self.mw.autocategorize_service.categorize_by_language,
            "deck_status": self.mw.autocategorize_service.categorize_by_deck_status,
            "achievements": self.mw.autocategorize_service.categorize_by_achievements,
            "pegi": self.mw.autocategorize_service.categorize_by_pegi,
        }

        for method in methods:
            if progress.wasCanceled():
                break

            if method == "tags":

                def tags_progress(index: int, name: str) -> None:
                    if progress.wasCanceled():
                        return
                    if index % 10 == 0:
                        progress.setLabelText(t("auto_categorize.status_tags", game=name[:30]))
                    progress.setValue(step + index)

                self.mw.autocategorize_service.categorize_by_tags(
                    games, tags_count=settings["tags_count"], progress_callback=tags_progress
                )

            elif method == "curator":
                progress.setLabelText(t("ui.enrichment.curator_starting"))
                progress.setValue(step)

                db_path = self._get_db_path()
                self.mw.autocategorize_service.categorize_by_curator(
                    games,
                    db_path=db_path,
                )

            elif method in methods_map:
                progress.setValue(step)
                # noinspection PyTypeChecker
                methods_map[method](games)

            step += len(games)

        self.mw.save_collections()
        progress.setValue(progress.maximum())
        progress.close()
        self.mw.populate_categories()
        UIHelper.show_success(self.mw, t("common.success"))

    # get db path from game service
    def _get_db_path(self):
        if hasattr(self.mw, "game_service") and self.mw.game_service:
            db = getattr(self.mw.game_service, "database", None)
            if db and hasattr(db, "db_path"):
                return db.db_path
        return None

    # smart collections

    def create_smart_collection(self) -> None:
        if not self.mw.game_manager or not self.mw.smart_collection_manager:
            return

        from steam_library_manager.ui.dialogs.smart_collection_dialog import SmartCollectionDialog

        dialog = SmartCollectionDialog(
            self.mw,
            self.mw.game_manager,
            self.mw.smart_collection_manager,
        )
        if dialog.exec():
            collection = dialog.get_result()
            if collection:
                count = len(self.mw.smart_collection_manager.evaluate_collection(collection))
                self.mw.smart_collection_manager.create(collection)
                self.mw.save_collections()
                self.mw.populate_categories()
                UIHelper.show_success(
                    self.mw,
                    t("ui.smart_collections.created", count=count),
                )

    def edit_smart_collection(self) -> None:
        existing = self._get_selected_smart_collection()
        if not existing:
            return

        from steam_library_manager.ui.dialogs.smart_collection_dialog import SmartCollectionDialog

        dialog = SmartCollectionDialog(
            self.mw,
            self.mw.game_manager,
            self.mw.smart_collection_manager,
            collection_to_edit=existing,
        )
        if dialog.exec():
            collection = dialog.get_result()
            if collection:
                count = self.mw.smart_collection_manager.update(collection)
                self.mw.save_collections()
                self.mw.populate_categories()
                UIHelper.show_success(
                    self.mw,
                    t("ui.smart_collections.updated", count=count),
                )

    def delete_smart_collection(self) -> None:
        existing = self._get_selected_smart_collection()
        if not existing:
            return

        if UIHelper.confirm(
            self.mw,
            t("ui.smart_collections.confirm_delete", name=existing.name),
            t("categories.delete_title"),
        ):
            self.mw.smart_collection_manager.delete(existing.collection_id)
            self.mw.save_collections()
            self.mw.populate_categories()
            UIHelper.show_success(self.mw, t("ui.smart_collections.deleted"))

    def refresh_smart_collections(self) -> None:
        if not self.mw.smart_collection_manager:
            return

        result = self.mw.smart_collection_manager.refresh()
        self.mw.save_collections()
        self.mw.populate_categories()
        UIHelper.show_success(
            self.mw,
            t("ui.smart_collections.refreshed", count=len(result)),
        )

    # get selected SC or warn user
    def _get_selected_smart_collection(self):
        if not self.mw.game_manager or not self.mw.smart_collection_manager:
            return None

        cats = self.mw.tree.get_selected_categories()
        if not cats:
            UIHelper.show_warning(self.mw, t("ui.smart_collections.select_collection"))
            return None

        existing = self.mw.smart_collection_manager.get_by_name(cats[0])
        if not existing:
            UIHelper.show_warning(self.mw, t("ui.smart_collections.not_smart"))
            return None

        return existing
