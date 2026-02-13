"""
Main application window for Steam Library Manager.

This module contains the primary application window that displays the game
library, handles user interactions, and coordinates between various managers
and dialogs. It provides the main interface for browsing, searching, and
managing Steam games.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from src.services.asset_service import AssetService

if TYPE_CHECKING:
    from src.services.category_service import CategoryService
    from src.services.metadata_service import MetadataService
    from src.services.autocategorize_service import AutoCategorizeService
    from src.services.game_service import GameService

from PyQt6.QtWidgets import QMainWindow, QToolBar
from PyQt6.QtCore import Qt, QThread, QTimer

from src.config import config
from src.core.game_manager import GameManager, Game
from src.core.localconfig_helper import LocalConfigHelper
from src.core.cloud_storage_parser import CloudStorageParser
from src.core.appinfo_manager import AppInfoManager

from src.integrations.steam_store import SteamStoreScraper
from src.services.search_service import SearchService  # <--- NEW

# Components
from src.ui.widgets.ui_helper import UIHelper

from src.utils.i18n import t

# Builders
from src.ui.builders import MenuBuilder, ToolbarBuilder, StatusbarBuilder, CentralWidgetBuilder

# Handlers
from src.ui.handlers import CategoryActionHandler, DataLoadHandler, SelectionHandler, CategoryChangeHandler
from src.ui.handlers.category_populator import CategoryPopulator

# Actions
from src.ui.actions import (
    FileActions,
    EditActions,
    ViewActions,
    ToolsActions,
    SteamActions,
    GameActions,
    SettingsActions,
)


class MainWindow(QMainWindow):
    """Primary application window for Steam Library Manager.

    Contains the game tree sidebar, details panel, menus, and toolbar.
    Coordinates between various managers for game loading, category editing,
    metadata management, and Steam authentication.

    Attributes:
        game_manager: Manages game data loading and storage.
        localconfig_helper: Parser for Steam's localconfig.vdf file.
        steam_scraper: Scraper for Steam Store data.
        appinfo_manager: Manager for appinfo.vdf metadata.
        selected_game: Currently selected single game.
        selected_games: List of currently selected games (multi-select).
        dialog_games: Games passed to the current dialog.
        steam_username: Logged in Steam username.
        'load_thread': Background thread game loading.
        store_check_thread: Background thread store availability checks.
        'progress_dialog': Progress dialog long operations.
    """

    def __init__(self):
        """Initializes the main window and loads initial data."""
        super().__init__()
        self.setWindowTitle(t("ui.main_window.title"))
        self.resize(1400, 800)

        # Managers
        self.game_manager: GameManager | None = None
        self.localconfig_helper: LocalConfigHelper | None = None
        self.cloud_storage_parser: CloudStorageParser | None = None
        self.steam_scraper: SteamStoreScraper | None = None
        self.appinfo_manager: AppInfoManager | None = None
        self.category_service: CategoryService | None = None  # Initialized after parsers
        self.metadata_service: MetadataService | None = None  # Initialized after appinfo_manager
        self.autocategorize_service: AutoCategorizeService | None = None  # Initialized after category_service
        self.game_service: GameService | None = None  # Initialized in _load_data
        self.asset_service = AssetService()  # Initialize immediately

        # NEW: Initialize SearchService
        self.search_service = SearchService()

        # NEW: Session/Token storage for modern Steam login
        self.session = None  # For password login (requests.Session)
        self.access_token = None  # For QR login (OAuth token)
        self.refresh_token = None  # For QR login (refresh token)

        # State
        self.selected_game: Game | None = None
        self.selected_games: list[Game] = []
        self.dialog_games: list[Game] = []
        self.steam_username: str | None = None
        self.current_search_query: str = ""  # Track active search

        # Threads & Dialogs
        self.store_check_thread: QThread | None = None

        # UI Builders (extracted from _create_ui for reuse on language change)
        self.menu_builder: MenuBuilder = MenuBuilder(self)
        self.toolbar_builder: ToolbarBuilder = ToolbarBuilder(self)
        self.statusbar_builder: StatusbarBuilder = StatusbarBuilder(self)

        # Initialize Action Handlers
        self.file_actions = FileActions(self)
        self.edit_actions = EditActions(self)
        self.view_actions = ViewActions(self)
        self.tools_actions = ToolsActions(self)
        self.steam_actions = SteamActions(self)
        self.game_actions = GameActions(self)
        self.settings_actions = SettingsActions(self)

        # UI Action Handlers (extracted category / context-menu logic)
        self.category_handler: CategoryActionHandler = CategoryActionHandler(self)
        self.selection_handler = SelectionHandler(self)
        self.category_change_handler = CategoryChangeHandler(self)
        self.data_load_handler = DataLoadHandler(self)
        self.category_populator = CategoryPopulator(self)

        self._create_ui()

        # Restore session BEFORE loading data so the access token
        # is available for the Steam Web API call
        self.steam_actions.restore_session()

        self._load_data()

    def _create_ui(self) -> None:
        """Initializes all UI components, menus, and layouts.

        Creates the menu bar, toolbar, central widget with splitter layout,
        game tree sidebar, details panel, search bar, and status bar.
        """
        # --- Menu bar (delegated to MenuBuilder) ---
        self.menu_builder.build(self.menuBar())
        self.user_label = self.menu_builder.user_label

        # --- Toolbar (delegated to ToolbarBuilder) ---
        self.toolbar = QToolBar()
        self.addToolBar(self.toolbar)
        self.toolbar_builder.build(self.toolbar)

        # --- Central Widget (delegated to CentralWidgetBuilder) ---
        central_builder = CentralWidgetBuilder(self)
        widgets = central_builder.build()

        self.tree = widgets["tree"]
        self.details_widget = widgets["details_widget"]
        self.search_entry = widgets["search_entry"]

        # --- Status bar (delegated to StatusbarBuilder) ---
        self.statusbar = self.statusBar()
        self.statusbar_builder.build(self.statusbar)
        self.stats_label = self.statusbar_builder.stats_label
        self.reload_btn = self.statusbar_builder.reload_btn

    def refresh_toolbar(self) -> None:
        """Rebuilds the toolbar based on current authentication state.

        Delegates entirely to ToolbarBuilder which handles clearing
        and recreating toolbar actions based on login state.
        """
        self.toolbar_builder.build(self.toolbar)

    # --- Main Logic ---

    def _load_data(self) -> None:
        """Performs the initial data loading sequence.

        Delegates to DataLoadHandler for all loading operations.
        """
        self.data_load_handler.load_data()

    def _populate_categories(self) -> None:
        """Refreshes the sidebar tree with current game data.

        Delegates to CategoryPopulator.populate().
        """
        self.category_populator.populate()

    def on_games_selected(self, games: list[Game]) -> None:
        """Handles multi-selection changes. Delegated to SelectionHandler."""
        self.selection_handler.on_games_selected(games)

    def on_game_selected(self, game: Game) -> None:
        """Handles single game selection. Delegated to SelectionHandler."""
        self.selection_handler.on_game_selected(game)

    def fetch_game_details_async(self, app_id: str, all_categories: list[str]) -> None:
        """Fetches game details async. Delegated to SelectionHandler."""
        self.selection_handler.fetch_game_details_async(app_id, all_categories)

    def _restore_game_selection(self, app_ids: list[str]) -> None:
        """Restores game selection. Delegated to SelectionHandler."""
        self.selection_handler.restore_game_selection(app_ids)

    def _apply_category_to_games(self, games: list[Game], category: str, checked: bool) -> None:
        """Applies category changes. Delegated to CategoryChangeHandler."""
        self.category_change_handler.apply_category_to_games(games, category, checked)

    def on_category_changed_from_details(self, app_id: str, category: str, checked: bool) -> None:
        """Handles category toggles. Delegated to CategoryChangeHandler."""
        self.category_change_handler.on_category_changed_from_details(app_id, category, checked)

    def on_games_dropped(self, games: list[Game], target_category: str) -> None:
        """Handles drag-and-drop. Delegated to CategoryChangeHandler."""
        self.category_change_handler.on_games_dropped(games, target_category)

    def on_game_right_click(self, game: Game, pos) -> None:
        """Shows context menu for a right-clicked game.

        Delegated to CategoryActionHandler.

        Args:
            game: The game that was right-clicked.
            pos: The screen position for the context menu.
        """
        self.category_handler.on_game_right_click(game, pos)

    def on_category_right_click(self, category: str, pos) -> None:
        """Shows context menu for a right-clicked category.

        Delegated to CategoryActionHandler.

        Args:
            category: The category name that was right-clicked (or "__MULTI__" for multi-select).
            pos: The screen position for the context menu.
        """
        self.category_handler.on_category_right_click(category, pos)

    @staticmethod
    def _save_settings(settings: dict) -> None:
        """Saves settings to the settings JSON file.

        Args:
            settings: Dictionary containing all settings values.
        """
        import json

        settings_file = config.DATA_DIR / "settings.json"
        data = {
            "ui_language": settings["ui_language"],
            "tags_language": settings["tags_language"],
            "tags_per_game": settings["tags_per_game"],
            "ignore_common_tags": settings["ignore_common_tags"],
            "steamgriddb_api_key": settings["steamgriddb_api_key"],
            "steam_api_key": settings.get("steam_api_key", ""),
            "max_backups": settings["max_backups"],
        }
        with open(settings_file, "w") as f:
            json.dump(data, f, indent=2)

    def set_status(self, text: str) -> None:
        """Updates the status bar message.

        Args:
            text (str): The status message to display.
        """
        self.statusbar.showMessage(text)

    def _update_statistics(self) -> None:
        """
        Update the statistics display in the status bar.

        Retrieves game statistics from the game manager and displays them
        in the permanent status bar widget, showing category count, games
        in categories, and total real games.
        """
        if not self.game_manager:
            return

        stats = self.game_manager.get_game_statistics()

        stats_text = t(
            "ui.main_window.statistics",
            category_count=stats["category_count"],
            games_in_categories=stats["games_in_categories"],
            total_games=stats["total_games"],
        )

        self.stats_label.setText(stats_text)

    def closeEvent(self, event) -> None:
        """Handle window close event with unified save dialog.

        Checks for both collection changes and metadata (VDF) changes.
        If changes exist, offers Save & Exit / Discard & Exit / Cancel.
        If no changes exist, asks for simple exit confirmation.

        Args:
            event: The close event from Qt.
        """
        parser = self._get_active_parser()
        has_collection_changes = parser is not None and parser.modified
        has_metadata_changes = self.appinfo_manager is not None and self.appinfo_manager.vdf_dirty

        if has_collection_changes or has_metadata_changes:
            result = self._ask_save_on_exit(has_collection_changes, has_metadata_changes)
            if result == "save":
                self._save_all_on_exit()
                event.accept()
            elif result == "discard":
                event.accept()
            else:
                event.ignore()
        else:
            if UIHelper.confirm(self, t("common.confirm_exit"), t("ui.main_window.title")):
                event.accept()
            else:
                event.ignore()

    def _ask_save_on_exit(self, has_collection_changes: bool, has_metadata_changes: bool) -> str:
        """Shows a 3-button dialog when unsaved changes exist on exit.

        Args:
            has_collection_changes: Whether cloud storage collections were modified.
            has_metadata_changes: Whether appinfo.vdf metadata was modified.

        Returns:
            ``"save"``, ``"discard"``, or ``"cancel"``.
        """
        from PyQt6.QtWidgets import QMessageBox

        filenames: list[str] = []
        if has_collection_changes:
            filenames.append("cloud-storage-namespace-1.json")
        if has_metadata_changes:
            filenames.append("appinfo.vdf")

        msg = QMessageBox(self)
        msg.setIcon(QMessageBox.Icon.Warning)
        msg.setWindowTitle(t("common.unsaved_changes_title"))
        msg.setText(t("common.unsaved_changes_msg", filenames=", ".join(filenames)))

        save_btn = msg.addButton(t("common.save_and_exit"), QMessageBox.ButtonRole.AcceptRole)
        discard_btn = msg.addButton(t("common.discard_and_exit"), QMessageBox.ButtonRole.DestructiveRole)
        msg.addButton(t("common.cancel"), QMessageBox.ButtonRole.RejectRole)
        msg.setDefaultButton(save_btn)

        msg.exec()

        clicked = msg.clickedButton()
        if clicked == save_btn:
            return "save"
        elif clicked == discard_btn:
            return "discard"
        return "cancel"

    def _save_all_on_exit(self) -> None:
        """Saves all pending changes before exiting.

        1. Saves collections if the parser has modifications.
        2. If VDF metadata is dirty: lazy-loads the binary (if not loaded),
           applies all modifications, writes to VDF with backup, and saves
           the JSON as well.
        """
        # 1. Save collections
        parser = self._get_active_parser()
        if parser and parser.modified:
            self._save_collections()

        # 2. Save VDF metadata
        if self.appinfo_manager and self.appinfo_manager.vdf_dirty:
            # Lazy-load binary if not yet loaded
            if not self.appinfo_manager.appinfo:
                self.appinfo_manager.load_appinfo()

            # Apply all tracked modifications to the binary
            for app_id, meta_data in self.appinfo_manager.modifications.items():
                modified = meta_data.get("modified", {})
                if modified and self.appinfo_manager.appinfo:
                    int_id = int(app_id)
                    if int_id in self.appinfo_manager.appinfo.apps:
                        self.appinfo_manager.appinfo.update_app_metadata(int_id, modified)

            # Write to VDF with backup
            self.appinfo_manager.write_to_vdf(backup=True)

            # Save JSON as well
            self.appinfo_manager.save_appinfo()

    # ========== Parser Wrapper Methods ==========

    def _get_active_parser(self) -> CloudStorageParser | None:
        """Get the active parser (cloud storage or localconfig)."""
        return self.cloud_storage_parser if self.cloud_storage_parser else self.localconfig_helper

    def _schedule_save(self) -> None:
        """Schedule a delayed save to batch multiple operations.

        Uses a 100ms timer to batch multiple rapid changes into a single save operation.
        This prevents excessive backups when performing bulk operations.
        """
        if hasattr(self, "_save_timer") and self._save_timer.isActive():
            self._save_timer.stop()

        self._save_timer = QTimer()
        self._save_timer.setSingleShot(True)
        self._save_timer.timeout.connect(self._save_collections)
        self._save_timer.start(100)  # 100ms delay

    # ------------------------------------------------------------------
    # Public persistence interface (used by extracted action handlers)
    # ------------------------------------------------------------------

    def save_collections(self) -> bool:
        """Persists collections to the active parser (cloud or local).

        Public wrapper around ``_save_collections`` so that external
        handler classes can trigger a save without accessing a protected member.

        Returns:
            True if the save succeeded, False otherwise.
        """
        return self._save_collections()

    def populate_categories(self) -> None:
        """Rebuilds the category tree widget from current game data.

        Public wrapper around ``_populate_categories`` for use by handlers.
        """
        self._populate_categories()

    def update_statistics(self) -> None:
        """Refreshes the statistics label in the status bar.

        Public wrapper around ``_update_statistics`` for use by handlers.
        """
        self._update_statistics()

    # ------------------------------------------------------------------

    def _save_collections(self) -> bool:
        """Save collections using the active parser.

        If the cloud storage file was modified externally since the last
        load, a warning is shown to the user after saving.
        """
        from src.ui.widgets.ui_helper import UIHelper

        # Only save to the active parser (cloud storage OR localconfig, not both!)
        if self.cloud_storage_parser:
            success = self.cloud_storage_parser.save()
            if success and getattr(self.cloud_storage_parser, "had_conflict", False):
                UIHelper.show_warning(
                    self,
                    t("ui.save.conflict_warning"),
                )
            return success
        elif self.localconfig_helper:
            return self.localconfig_helper.save()
        return False

    def _add_app_category(self, app_id: str, category: str) -> None:
        """Add category to app using CategoryService."""
        if self.category_service:
            self.category_service.add_app_to_category(app_id, category)

    def _remove_app_category(self, app_id: str, category: str) -> None:
        """Remove category from app using CategoryService."""
        if self.category_service:
            self.category_service.remove_app_from_category(app_id, category)

    def _rename_category(self, old_name: str, new_name: str) -> None:
        """Rename category using CategoryService."""
        if self.category_service:
            try:
                self.category_service.rename_category(old_name, new_name)
            except ValueError as e:
                UIHelper.show_error(self, str(e))

    def _delete_category(self, category: str) -> None:
        """Delete category using CategoryService."""
        if self.category_service:
            self.category_service.delete_category(category)

    def find_missing_metadata(self) -> None:
        """Delegates to ToolsActions (required by MenuBuilder)."""
        self.tools_actions.find_missing_metadata()

    def check_store_availability(self, game: Game) -> None:
        """Delegates to ToolsActions (required by Context Menus)."""
        self.tools_actions.check_store_availability(game)

    def keyPressEvent(self, event) -> None:
        """Handle key press events.

        Args:
            event: The key press event.
        """
        # ESC key: Clear selection
        if event.key() == Qt.Key.Key_Escape:
            if self.selected_games:
                self.selected_games = []
                self.tree.clearSelection()
                self.details_widget.clear()
                self.set_status(t("ui.main_window.status_ready"))
        else:
            # Pass other keys to parent
            super().keyPressEvent(event)
