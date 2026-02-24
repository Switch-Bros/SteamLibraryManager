"""
Action handler for Edit menu and related operations.

Extracts the following logic from MainWindow:
  - Auto-Categorization (Dialogs & Execution)
  - Metadata Editing (Single & Bulk)
  - PEGI Overrides
  - Metadata Restoration

Connects back to MainWindow to access services and update UI.
"""

from __future__ import annotations

__all__ = ["EditActions"]

from typing import TYPE_CHECKING

from PyQt6.QtWidgets import QMessageBox, QApplication

from src.core.game_manager import Game
from src.services.curator_client import CuratorRecommendation

# Dialogs
from src.ui.dialogs.auto_categorize_dialog import AutoCategorizeDialog
from src.ui.dialogs.metadata_dialogs import BulkMetadataEditDialog, MetadataRestoreDialog
from src.ui.dialogs.metadata_edit_dialog import MetadataEditDialog
from src.ui.widgets.ui_helper import UIHelper
from src.utils.i18n import t

if TYPE_CHECKING:
    from src.ui.main_window import MainWindow


class EditActions:
    """
    Handles all Edit-related actions (Metadata, Categories).

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
                    progress.setValue(step + index)
                    if index % 10 == 0:
                        progress.setLabelText(t("auto_categorize.status_tags", game=name[:30]))
                    QApplication.processEvents()

                self.mw.autocategorize_service.categorize_by_tags(
                    games, tags_count=settings["tags_count"], progress_callback=tags_progress
                )

            elif method == "curator":
                curator_url = settings.get("curator_url", "")
                rec_strings = settings.get(
                    "curator_recommendations", ["recommended", "not_recommended", "informational"]
                )

                rec_map = {
                    "recommended": CuratorRecommendation.RECOMMENDED,
                    "not_recommended": CuratorRecommendation.NOT_RECOMMENDED,
                    "informational": CuratorRecommendation.INFORMATIONAL,
                }
                included_types = {rec_map[r] for r in rec_strings if r in rec_map}

                progress.setValue(step)
                progress.setLabelText(t("auto_categorize.curator_fetching"))
                QApplication.processEvents()

                try:
                    self.mw.autocategorize_service.categorize_by_curator(
                        games,
                        curator_url=curator_url,
                        included_types=included_types,
                    )
                except (ValueError, ConnectionError) as exc:
                    UIHelper.show_error(self.mw, t("auto_categorize.curator_error_fetch", error=str(exc)))

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

    # ------------------------------------------------------------------
    # Metadata Editing
    # ------------------------------------------------------------------

    def edit_game_metadata(self, game: Game) -> None:
        """Opens the metadata edit dialog for a single game.

        Lazy-loads the binary appinfo.vdf on first access if not yet loaded.
        VDF is NOT written per-edit; instead it is written on exit via
        closeEvent / _save_all_on_exit().

        Args:
            game: The game to edit.
        """
        if not self.mw.metadata_service:
            return

        # Lazy-load binary VDF on first metadata edit
        if self.mw.appinfo_manager and not self.mw.appinfo_manager.appinfo:
            self.mw.appinfo_manager.load_appinfo()

        meta = self.mw.metadata_service.get_game_metadata(game.app_id, game)
        original_meta = self.mw.metadata_service.get_original_metadata(game.app_id, meta.copy())

        dialog = MetadataEditDialog(self.mw, game.name, meta, original_meta)

        if dialog.exec():
            new_meta = dialog.get_metadata()
            if new_meta:
                self.mw.metadata_service.set_game_metadata(game.app_id, new_meta)

                if new_meta.get("name"):
                    game.name = new_meta["name"]

                self.mw.populate_categories()
                self.mw.on_game_selected(game)
                UIHelper.show_success(self.mw, t("ui.metadata_editor.updated_single", game=game.name))

    def bulk_edit_metadata(self) -> None:
        """Opens the bulk metadata edit dialog for selected games."""
        if not self.mw.selected_games or not self.mw.metadata_service:
            UIHelper.show_warning(self.mw, t("ui.errors.no_selection"))
            return

        game_names = [g.name for g in self.mw.selected_games]
        dialog = BulkMetadataEditDialog(self.mw, self.mw.selected_games, game_names)

        if dialog.exec():
            settings = dialog.get_metadata()
            if settings:
                # Revert mode: restore all selected games to original metadata
                if settings.get("__revert_to_original__"):
                    count = self.mw.metadata_service.restore_games_to_original(self.mw.selected_games)
                    self.mw.file_actions.refresh_data()
                    UIHelper.show_success(
                        self.mw,
                        t("ui.metadata_editor.bulk_reverted", count=count),
                    )
                    return

                # Normal bulk edit
                name_mods = settings.pop("name_modifications", None)
                count = self.mw.metadata_service.apply_bulk_metadata(self.mw.selected_games, settings, name_mods)
                self.mw.populate_categories()
                UIHelper.show_success(self.mw, t("ui.metadata_editor.updated_bulk", count=count))

    def on_pegi_override_requested(self, app_id: str, rating: str) -> None:
        """
        Handles PEGI override requests from GameDetailsWidget.

        Args:
            app_id: The AppID of the game.
            rating: The new PEGI rating (or empty to remove).
        """
        if not self.mw.appinfo_manager:
            return

        # Save override
        if rating:
            self.mw.appinfo_manager.set_app_metadata(app_id, {"pegi_rating": rating})
            self.mw.appinfo_manager.save_appinfo()
            UIHelper.show_success(self.mw, t("ui.pegi_selector.saved", rating=rating))
        else:
            # Remove override
            if app_id in self.mw.appinfo_manager.modifications:
                mod = self.mw.appinfo_manager.modifications[app_id].get("modified", {})
                if "pegi_rating" in mod:
                    del self.mw.appinfo_manager.modifications[app_id]["modified"]["pegi_rating"]
                    self.mw.appinfo_manager.save_appinfo()
                    UIHelper.show_success(self.mw, t("ui.pegi_selector.removed"))

        # Update UI
        if self.mw.game_manager:
            game = self.mw.game_manager.get_game(app_id)
            if game:
                if rating:
                    game.pegi_rating = rating
                else:
                    # Restore original by re-fetching details
                    # This re-applies data from store cache (including original PEGI)
                    self.mw.game_manager.fetch_game_details(app_id)

                    # Re-apply other overrides (name, dev, etc.) just in case
                    if self.mw.appinfo_manager:
                        self.mw.game_manager.apply_metadata_overrides(self.mw.appinfo_manager)

                self.mw.on_game_selected(game)

    def restore_metadata_changes(self) -> None:
        """Opens dialog to restore metadata changes."""
        if not self.mw.metadata_service:
            return

        mod_count = self.mw.metadata_service.get_modification_count()
        if mod_count == 0:
            UIHelper.show_success(self.mw, t("ui.metadata_editor.no_changes_to_restore"))
            return

        dialog = MetadataRestoreDialog(self.mw, mod_count)
        # Assuming MetadataRestoreDialog also uses custom buttons internally
        if dialog.exec() and dialog.should_restore():
            try:
                restored = self.mw.metadata_service.restore_modifications()
                if restored > 0:
                    UIHelper.show_success(self.mw, t("ui.metadata_editor.restored_count", count=restored))
                    self.mw.file_actions.refresh_data()
            except Exception as e:
                UIHelper.show_error(self.mw, str(e))
