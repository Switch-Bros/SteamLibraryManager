"""Action handler for auto-categorization and Smart Collections.

Connects back to MainWindow to access services and update UI.
Metadata editing operations are in metadata_actions.py.
"""

from __future__ import annotations

__all__ = ["EditActions"]

from typing import TYPE_CHECKING

from PyQt6.QtWidgets import QMessageBox

from src.core.game_manager import Game
from src.ui.dialogs.auto_categorize_dialog import AutoCategorizeDialog
from src.ui.widgets.ui_helper import UIHelper
from src.utils.i18n import t

if TYPE_CHECKING:
    from src.ui.main_window import MainWindow


class EditActions:
    """Handles auto-categorization and Smart Collection actions.

    Attributes:
        mw: Back-reference to the owning MainWindow instance.
        dialog_games: Temporary storage for games being processed in dialogs.
    """

    def __init__(self, main_window: "MainWindow") -> None:
        """
        Initialize the EditActions handler.

        Args:
            main_window: The main application window.
        """
        self.mw = main_window
        self.dialog_games: list[Game] = []

    # ------------------------------------------------------------------
    # Auto-Categorization
    # ------------------------------------------------------------------

    def auto_categorize(self) -> None:
        """Opens the auto-categorize dialog for selected or uncategorized games."""
        if self.mw.selected_games:
            self._show_auto_categorize_dialog(self.mw.selected_games, None)
        elif self.mw.game_manager:
            self._show_auto_categorize_dialog(self.mw.game_manager.get_uncategorized_games(), None)

    def auto_categorize_selected(self) -> None:
        """Opens the auto-categorize dialog for currently selected games."""
        if self.mw.selected_games:
            self._show_auto_categorize_dialog(self.mw.selected_games, None)

    def auto_categorize_single(self, game: Game) -> None:
        """
        Opens the auto-categorize dialog for a single game.

        Args:
            game: The game to auto-categorize.
        """
        self._show_auto_categorize_dialog([game], None)

    def auto_categorize_category(self, category: str) -> None:
        """
        Opens the auto-categorize dialog for games in a specific category.

        Args:
            category: The name of the category.
        """
        if not self.mw.game_manager:
            return

        if category == t("categories.all_games"):
            self._show_auto_categorize_dialog(self.mw.game_manager.get_real_games(), category)
        elif category == t("categories.uncategorized"):
            self._show_auto_categorize_dialog(self.mw.game_manager.get_uncategorized_games(), category)
        else:
            self._show_auto_categorize_dialog(self.mw.game_manager.get_games_by_category(category), category)

    def _show_auto_categorize_dialog(self, games: list[Game], category_name: str | None) -> None:
        """
        Internal helper to show the dialog.

        Args:
            games: List of games to process.
            category_name: Optional source category name.
        """
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

    def _check_and_start(self, settings: dict, dialog: "AutoCategorizeDialog") -> None:
        """
        Checks cache coverage before starting auto-categorization.
        Uses custom buttons to avoid English text.

        Args:
            settings: The settings dictionary from the dialog.
            dialog: The dialog instance to close on success.
        """
        # Check tags requirement
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
            actual_games = self.mw.game_manager.get_real_games()
        else:
            actual_games = self.dialog_games

        # Check coverage
        coverage = self.mw.autocategorize_service.get_cache_coverage(actual_games)

        if coverage["percentage"] >= 50:
            dialog.accept()
            self._do_auto_categorize(settings)
            return

        # Show warning with CUSTOM buttons
        missing = coverage["missing"]
        time_str = self.mw.autocategorize_service.estimate_time(missing)

        msg_box = QMessageBox(self.mw)
        msg_box.setIcon(QMessageBox.Icon.Warning)
        msg_box.setWindowTitle(t("auto_categorize.cache_warning_title"))
        msg_box.setText(
            t(
                "auto_categorize.cache_warning_message",
                cached=coverage["cached"],
                total=coverage["total"],
                time=time_str,
            )
        )

        # IMPORTANT: Manual buttons, no StandardButtons
        yes_button = msg_box.addButton(t("common.yes"), QMessageBox.ButtonRole.YesRole)
        no_button = msg_box.addButton(t("common.no"), QMessageBox.ButtonRole.NoRole)
        msg_box.setDefaultButton(no_button)

        msg_box.exec()

        if msg_box.clickedButton() == yes_button:
            dialog.accept()
            self._do_auto_categorize(settings)

    def _do_auto_categorize(self, settings: dict) -> None:
        """
        Executes the auto-categorization process.
        Iterates through selected methods and updates progress.

        Args:
            settings: Configuration dictionary.
        """
        # noinspection PyProtectedMember
        parser = self.mw._get_active_parser()
        if not settings or not parser or not self.mw.autocategorize_service:
            return

        games = self.mw.game_manager.get_real_games() if settings["scope"] == "all" else self.dialog_games
        methods = settings["methods"]

        progress = UIHelper.create_progress_dialog(
            self.mw,
            t("auto_categorize.processing", current=0, total=len(games)),
            maximum=len(methods) * len(games),
        )

        step = 0

        # Mapping simple methods to avoid code duplication
        simple_methods = {
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

            elif method in simple_methods:
                # Update progress for fast batch operations
                progress.setValue(step)
                # Call the service method
                # noinspection PyTypeChecker
                simple_methods[method](games)

            step += len(games)

        self.mw.save_collections()
        progress.setValue(progress.maximum())
        progress.close()
        self.mw.populate_categories()
        UIHelper.show_success(self.mw, t("common.success"))

    def _get_db_path(self):
        """Returns the database file path from the active game service.

        Returns:
            Path to the SQLite database, or None if not available.
        """
        if hasattr(self.mw, "game_service") and self.mw.game_service:
            db = getattr(self.mw.game_service, "database", None)
            if db and hasattr(db, "db_path"):
                return db.db_path
        return None

    # ------------------------------------------------------------------
    # Smart Collections
    # ------------------------------------------------------------------

    def create_smart_collection(self) -> None:
        """Opens SmartCollectionDialog for creating a new Smart Collection."""
        if not self.mw.game_manager or not self.mw.smart_collection_manager:
            return

        from src.ui.dialogs.smart_collection_dialog import SmartCollectionDialog

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
        """Opens SmartCollectionDialog for editing the selected Smart Collection."""
        existing = self._get_selected_smart_collection()
        if not existing:
            return

        from src.ui.dialogs.smart_collection_dialog import SmartCollectionDialog

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
        """Deletes the selected Smart Collection after confirmation."""
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
        """Re-evaluates all Smart Collections and refreshes the tree."""
        if not self.mw.smart_collection_manager:
            return

        result = self.mw.smart_collection_manager.refresh()
        self.mw.save_collections()
        self.mw.populate_categories()
        UIHelper.show_success(
            self.mw,
            t("ui.smart_collections.refreshed", count=len(result)),
        )

    def _get_selected_smart_collection(self):
        """Returns the selected Smart Collection, or None with a user warning.

        Shared guard logic for edit / delete Smart Collection actions.
        Checks that game_manager and smart_collection_manager are available,
        that a category is selected, and that it is a Smart Collection.

        Returns:
            The SmartCollection object, or None if any check fails.
        """
        if not self.mw.game_manager or not self.mw.smart_collection_manager:
            return None

        selected_cats = self.mw.tree.get_selected_categories()
        if not selected_cats:
            UIHelper.show_warning(self.mw, t("ui.smart_collections.select_collection"))
            return None

        existing = self.mw.smart_collection_manager.get_by_name(selected_cats[0])
        if not existing:
            UIHelper.show_warning(self.mw, t("ui.smart_collections.not_smart"))
            return None

        return existing
