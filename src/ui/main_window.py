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
    from src.services.smart_collections.smart_collection_manager import SmartCollectionManager

from PyQt6.QtWidgets import QMainWindow, QToolBar
from PyQt6.QtCore import QThread, QTimer

from src.core.game_manager import GameManager, Game
from src.core.localconfig_helper import LocalConfigHelper
from src.core.cloud_storage_parser import CloudStorageParser
from src.core.appinfo_manager import AppInfoManager

from src.integrations.steam_store import SteamStoreScraper
from src.services.filter_service import FilterService
from src.services.search_service import SearchService

# Components
from src.ui.widgets.ui_helper import UIHelper

from src.utils.i18n import t
from src.version import __app_name__

# Builders
from src.ui.builders import (
    MenuBuilder,
    ToolbarBuilder,
    StatusbarBuilder,
    CentralWidgetBuilder,
)

# Handlers
from src.ui.handlers import (
    CategoryActionHandler,
    DataLoadHandler,
    SelectionHandler,
    CategoryChangeHandler,
    CategoryPopulator,
)
from src.ui.handlers.keyboard_handler import KeyboardHandler

# Actions
from src.ui.actions import (
    FileActions,
    EditActions,
    MetadataActions,
    ViewActions,
    ToolsActions,
    SteamActions,
    GameActions,
    SettingsActions,
    ProfileActions,
)
from src.ui.actions.enrichment_actions import EnrichmentActions
from src.ui.actions.enrichment_starters import EnrichmentStarters


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
        self.setWindowTitle(__app_name__)
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
        self.game_service: GameService | None = None  # Initialized by BootstrapService
        self.smart_collection_manager: SmartCollectionManager | None = None
        self.asset_service = AssetService()  # Initialize immediately

        # Services
        self.search_service = SearchService()
        self.filter_service = FilterService()

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
        self.metadata_actions = MetadataActions(self)
        self.view_actions = ViewActions(self)
        self.tools_actions = ToolsActions(self)
        self.steam_actions = SteamActions(self)
        self.game_actions = GameActions(self)
        self.settings_actions = SettingsActions(self)
        self.profile_actions = ProfileActions(self)
        self.enrichment_actions = EnrichmentActions(self)
        self.enrichment_starters = EnrichmentStarters(self)

        # UI Action Handlers (extracted category / context-menu logic)
        self.category_handler: CategoryActionHandler = CategoryActionHandler(self)
        self.selection_handler = SelectionHandler(self)
        self.category_change_handler = CategoryChangeHandler(self)
        self.data_load_handler = DataLoadHandler(self)
        self.category_populator = CategoryPopulator(self)
        self.keyboard_handler = KeyboardHandler(self)

        self._create_ui()
        self.keyboard_handler.register_shortcuts()
        self.keyboard_handler.install_event_filter()
        self.show()

        # Non-blocking startup via BootstrapService
        self._init_bootstrap_service()

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
        self.loading_label = widgets["loading_label"]
        self.progress_bar = widgets["progress_bar"]

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

    # --- Bootstrap & Loading ---

    def _init_bootstrap_service(self) -> None:
        """Create the BootstrapService, connect signals, and start it."""
        from src.services.bootstrap_service import BootstrapService

        self.bootstrap_service: BootstrapService = BootstrapService(self)
        self.bootstrap_service.loading_started.connect(self._on_loading_started)
        self.bootstrap_service.load_progress.connect(self._on_load_progress)
        self.bootstrap_service.persona_resolved.connect(self._on_persona_resolved)
        self.bootstrap_service.session_restored.connect(self._on_session_restored)
        self.bootstrap_service.bootstrap_complete.connect(self._on_bootstrap_complete)
        self.bootstrap_service.start()

    def _on_loading_started(self) -> None:
        """Show tree loading placeholder and progress bar."""
        self.tree.set_loading_state(True)
        self.loading_label.setText(t("ui.bootstrap.loading_games"))
        self.loading_label.setVisible(True)
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(True)
        self.set_status(t("common.loading"))

    def _on_load_progress(self, step: str, current: int, total: int) -> None:
        """Update inline progress bar and label.

        Args:
            step: Description of the current loading step.
            current: Current progress count.
            total: Total items to process.
        """
        self.loading_label.setText(step)
        if total > 0:
            percent = int((current / total) * 100)
            self.progress_bar.setValue(percent)

    def _on_persona_resolved(self, display_name: str) -> None:
        """Update the user label when persona name is fetched.

        Args:
            display_name: The resolved persona name or Steam ID.
        """
        self.user_label.setText(t("ui.main_window.user_label", user_id=display_name))

    def _on_session_restored(self, success: bool) -> None:
        """Rebuild toolbar if session was restored.

        Args:
            success: Whether the session was restored successfully.
        """
        if success:
            self.refresh_toolbar()

    def _on_bootstrap_complete(self) -> None:
        """Hide loading indicators when bootstrap is finished."""
        self.loading_label.setVisible(False)
        self.progress_bar.setVisible(False)

    def _populate_categories(self) -> None:
        """Refreshes the sidebar tree with current game data.

        Delegates to CategoryPopulator.populate().
        """
        self.category_populator.populate()

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

    def set_status(self, text: str) -> None:
        """Updates the status bar message.

        Args:
            text (str): The status message to display.
        """
        self.statusbar.showMessage(text)

    def _update_statistics(self) -> None:
        """Updates the statistics display in the status bar."""
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
        self.keyboard_handler.remove_event_filter()

        parser = self._get_active_parser()
        has_collection_changes = parser is not None and parser.modified
        has_metadata_changes = self.appinfo_manager is not None and self.appinfo_manager.vdf_dirty

        if has_collection_changes or has_metadata_changes:
            result = self.file_actions.ask_save_on_exit(has_collection_changes, has_metadata_changes)
            if result == "save":
                self._save_all_on_exit()
                self._stop_background_threads()
                event.accept()
            elif result == "discard":
                self._stop_background_threads()
                event.accept()
            else:
                event.ignore()
        else:
            if UIHelper.confirm(self, t("ui.exit.confirm"), __app_name__):
                self._stop_background_threads()
                event.accept()
            else:
                event.ignore()

    def _stop_background_threads(self) -> None:
        """Stops all running background threads to prevent SIGABRT on exit."""
        threads_to_stop: list[QThread] = []

        # Collect threads from main window
        if self.store_check_thread and self.store_check_thread.isRunning():
            threads_to_stop.append(self.store_check_thread)

        # Collect threads from action handlers
        for handler in (
            getattr(self, "enrichment_starters", None),
            getattr(self, "enrichment_actions", None),
            getattr(self, "tools_actions", None),
        ):
            if handler:
                for attr in ("_tag_import_thread", "_enrichment_thread", "_store_check_thread"):
                    thread = getattr(handler, attr, None)
                    if isinstance(thread, QThread) and thread.isRunning():
                        threads_to_stop.append(thread)

        # Request cancellation and wait
        for thread in threads_to_stop:
            cancel = getattr(thread, "cancel", None)
            if callable(cancel):
                cancel()

        for thread in threads_to_stop:
            thread.quit()
            thread.wait(3000)  # 3 second timeout

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
        """Persists collections to the active parser."""
        return self._save_collections()

    def populate_categories(self) -> None:
        """Rebuilds the category tree from current data."""
        self._populate_categories()

    def update_statistics(self) -> None:
        """Refreshes the statistics label in the status bar."""
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

    # ------------------------------------------------------------------
    # Keyboard & Easter Egg delegation
    # ------------------------------------------------------------------

    def eventFilter(self, obj, event) -> bool:
        """Delegates to KeyboardHandler for surprise code detection."""
        self.keyboard_handler.handle_event_filter(obj, event)
        return super().eventFilter(obj, event)

    def keyPressEvent(self, event) -> None:
        """Delegates to KeyboardHandler for shortcut processing."""
        if not self.keyboard_handler.handle_key_press(event):
            super().keyPressEvent(event)
