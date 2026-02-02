"""
Main application window for Steam Library Manager.

This module contains the primary application window that displays the game
library, handles user interactions, and coordinates between various managers
and dialogs. It provides the main interface for browsing, searching, and
managing Steam games.
"""
from pathlib import Path
from typing import Optional, List, TYPE_CHECKING

if TYPE_CHECKING:
    from src.services.category_service import CategoryService
    from src.services.metadata_service import MetadataService
    from src.services.autocategorize_service import AutoCategorizeService
    from src.services.game_service import GameService
    from src.services.asset_service import AssetService

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLineEdit, QPushButton, QLabel, QToolBar, QMenu,
    QMessageBox, QSplitter, QProgressDialog, QApplication
)
from PyQt6.QtCore import Qt, QThread, QTimer, pyqtSignal

import requests
# noinspection PyPep8Naming
import xml.etree.ElementTree as ET

from src.config import config
from src.core.game_manager import GameManager, Game
from src.core.localconfig_parser import LocalConfigParser
from src.core.cloud_storage_parser import CloudStorageParser
from src.core.appinfo_manager import AppInfoManager
from src.core.steam_auth import SteamAuthManager
from src.integrations.steam_store import SteamStoreScraper
from src.services.game_service import GameService
from src.services.asset_service import AssetService

# Dialogs
from src.ui.auto_categorize_dialog import AutoCategorizeDialog
from src.ui.metadata_dialogs import (
    MetadataEditDialog,
    BulkMetadataEditDialog,
    MetadataRestoreDialog
)
from src.ui.missing_metadata_dialog import MissingMetadataDialog
from src.ui.settings_dialog import SettingsDialog
from src.ui.vdf_merger_dialog import VdfMergerDialog

# Components
from src.ui.game_details_widget import GameDetailsWidget
from src.ui.components.category_tree import GameTreeWidget
from src.ui.components.ui_helper import UIHelper

from src.utils.i18n import t, init_i18n
from src.ui.builders import MenuBuilder, ToolbarBuilder, StatusbarBuilder


class GameLoadThread(QThread):
    """Background thread for loading games without blocking the UI.

    Loads game data from Steam API and local files in a separate thread,
    emitting progress updates that can be displayed in a progress dialog.

    Attributes:
        game_service: The GameService instance to use for loading.
        user_id: The Steam user ID to load games for.

    Signals:
        progress_update: Emitted during loading with (step_name, current, total).
        finished: Emitted when loading completes with success status.
    """

    progress_update = pyqtSignal(str, int, int)
    finished = pyqtSignal(bool)

    def __init__(self, game_service: GameService, user_id: str):
        """Initializes the game load thread.

        Args:
            game_service: The GameService instance to use for loading.
            user_id: The Steam user ID to load games for.
        """
        super().__init__()
        self.game_service = game_service
        self.user_id = user_id

    def run(self) -> None:
        """Executes the game loading process.

        Calls the game service's load_games method with a progress callback
        and emits the finished signal with the result.
        """

        def progress_callback(step: str, current: int, total: int):
            self.progress_update.emit(step, current, total)

        success = self.game_service.load_games(self.user_id, progress_callback)
        self.finished.emit(success)


class MainWindow(QMainWindow):
    """Primary application window for Steam Library Manager.

    Contains the game tree sidebar, details panel, menus, and toolbar.
    Coordinates between various managers for game loading, category editing,
    metadata management, and Steam authentication.

    Attributes:
        game_manager: Manages game data loading and storage.
        vdf_parser: Parser for Steam's localconfig.vdf file.
        steam_scraper: Scraper for Steam Store data.
        appinfo_manager: Manager for appinfo.vdf metadata.
        auth_manager: Handles Steam OpenID authentication.
        selected_game: Currently selected single game.
        selected_games: List of currently selected games (multi-select).
        dialog_games: Games passed to the current dialog.
        steam_username: Logged in Steam username.
        load_thread: Background thread for game loading.
        store_check_thread: Background thread for store availability checks.
        progress_dialog: Progress dialog for long operations.
    """

    def __init__(self):
        """Initializes the main window and loads initial data."""
        super().__init__()
        self.setWindowTitle(t('ui.main_window.title'))
        self.resize(1400, 800)

        # Managers
        self.game_manager: Optional[GameManager] = None
        self.vdf_parser: Optional[LocalConfigParser] = None
        self.cloud_storage_parser: Optional[CloudStorageParser] = None
        self.steam_scraper: Optional[SteamStoreScraper] = None
        self.appinfo_manager: Optional[AppInfoManager] = None
        self.category_service: Optional['CategoryService'] = None  # Initialized after parsers
        self.metadata_service: Optional['MetadataService'] = None  # Initialized after appinfo_manager
        self.autocategorize_service: Optional['AutoCategorizeService'] = None  # Initialized after category_service
        self.game_service: Optional[GameService] = None  # Initialized in _load_data
        self.asset_service = AssetService()  # Initialize immediately

        # Auth Manager
        self.auth_manager = SteamAuthManager()
        self.auth_manager.auth_success.connect(self._on_steam_login_success)
        self.auth_manager.auth_error.connect(self._on_steam_login_error)

        # State
        self.selected_game: Optional[Game] = None
        self.selected_games: List[Game] = []
        self.dialog_games: List[Game] = []
        self.steam_username: Optional[str] = None
        self.current_search_query: str = ""  # Track active search

        # Performance: Cache for _populate_categories
        self._categories_cache: Optional[dict] = None
        self._cache_invalidated: bool = True

        # Threads & Dialogs
        self.load_thread: Optional[GameLoadThread] = None
        self.store_check_thread: Optional[QThread] = None
        self.progress_dialog: Optional[QProgressDialog] = None

        # UI Builders (extracted from _create_ui for reuse on language change)
        self.menu_builder: MenuBuilder = MenuBuilder(self)
        self.toolbar_builder: ToolbarBuilder = ToolbarBuilder(self)
        self.statusbar_builder: StatusbarBuilder = StatusbarBuilder(self)

        self._create_ui()
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

        # Central Widget
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(5, 5, 5, 5)

        splitter = QSplitter(Qt.Orientation.Horizontal)

        # LEFT SIDE
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(2)

        # Search
        search_layout = QHBoxLayout()
        search_layout.addWidget(QLabel(t('ui.main_window.search_icon')))
        self.search_entry = QLineEdit()
        self.search_entry.setPlaceholderText(t('ui.main_window.search_placeholder'))
        # noinspection PyUnresolvedReferences
        self.search_entry.textChanged.connect(self.on_search)
        search_layout.addWidget(self.search_entry)

        clear_btn = QPushButton(t('common.clear'))
        # noinspection PyUnresolvedReferences
        clear_btn.clicked.connect(self.clear_search)
        clear_btn.setMaximumWidth(30)
        search_layout.addWidget(clear_btn)
        left_layout.addLayout(search_layout)

        # Tree Controls
        btn_layout = QHBoxLayout()
        expand_btn = QPushButton(f"▼ {t('ui.menu.view.expand_all')}")
        # noinspection PyUnresolvedReferences
        expand_btn.clicked.connect(lambda: self.tree.expandAll())
        btn_layout.addWidget(expand_btn)

        collapse_btn = QPushButton(f"▲ {t('ui.menu.view.collapse_all')}")
        # noinspection PyUnresolvedReferences
        collapse_btn.clicked.connect(lambda: self.tree.collapseAll())
        btn_layout.addWidget(collapse_btn)
        left_layout.addLayout(btn_layout)

        # Tree Widget
        self.tree = GameTreeWidget()
        # noinspection PyUnresolvedReferences,DuplicatedCode
        self.tree.game_clicked.connect(self.on_game_selected)
        # noinspection PyUnresolvedReferences
        self.tree.game_right_clicked.connect(self.on_game_right_click)
        # noinspection PyUnresolvedReferences
        self.tree.category_right_clicked.connect(self.on_category_right_click)
        # noinspection PyUnresolvedReferences
        self.tree.selection_changed.connect(self._on_games_selected)
        # noinspection PyUnresolvedReferences
        self.tree.games_dropped.connect(self._on_games_dropped)
        left_layout.addWidget(self.tree)

        splitter.addWidget(left_widget)

        # RIGHT SIDE (Details)
        self.details_widget = GameDetailsWidget()
        # noinspection PyUnresolvedReferences
        self.details_widget.category_changed.connect(self._on_category_changed_from_details)
        # noinspection PyUnresolvedReferences
        self.details_widget.edit_metadata.connect(self.edit_game_metadata)
        # noinspection PyUnresolvedReferences
        self.details_widget.pegi_override_requested.connect(self._on_pegi_override_requested)
        splitter.addWidget(self.details_widget)

        splitter.setSizes([350, 1050])
        layout.addWidget(splitter)

        # --- Status bar (delegated to StatusbarBuilder) ---
        self.statusbar = self.statusBar()
        self.statusbar_builder.build(self.statusbar)
        self.stats_label = self.statusbar_builder.stats_label
        self.reload_btn = self.statusbar_builder.reload_btn

    def _refresh_toolbar(self) -> None:
        """Rebuilds the toolbar based on current authentication state.

        Delegates entirely to ToolbarBuilder which handles clearing
        and recreating toolbar actions based on login state.
        """
        self.toolbar_builder.build(self.toolbar)

    @staticmethod
    def _fetch_steam_persona_name(steam_id: str) -> str:
        """Fetches the public persona name from Steam Community XML.

        Args:
            steam_id: The Steam ID64 to look up.

        Returns:
            The persona name if found, otherwise the original steam_id.
        """
        try:
            url = f"https://steamcommunity.com/profiles/{steam_id}/?xml=1"
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                tree = ET.fromstring(response.content)
                steam_id_element = tree.find('steamID')
                if steam_id_element is not None and steam_id_element.text:
                    return steam_id_element.text
        except Exception as e:
            print(t('logs.auth.profile_error', error=str(e)))
        return steam_id

    # --- OpenID Login Logic ---

    def _start_steam_login(self) -> None:
        """Initiates the Steam OpenID authentication process.

        Opens an embedded login dialog for Steam login.
        """
        self.auth_manager.start_login(parent=self)

    def _on_steam_login_success(self, steam_id_64: str) -> None:
        """Handles successful Steam authentication.

        Args:
            steam_id_64: The authenticated user's Steam ID64.
        """
        print(t('logs.auth.login_success', id=steam_id_64))
        self.set_status(t('ui.login.status_success'))
        UIHelper.show_success(self, t('ui.login.status_success'), t('ui.login.title'))

        config.STEAM_USER_ID = steam_id_64
        # Save immediately so login persists after restart
        config.save()

        # Fetch persona name
        self.steam_username = self._fetch_steam_persona_name(steam_id_64)

        # Update user label
        display_text = self.steam_username if self.steam_username else steam_id_64
        self.user_label.setText(t('ui.main_window.user_label', user_id=display_text))

        # Rebuild toolbar to show name instead of login button
        self._refresh_toolbar()

        if self.game_manager:
            self._load_games_with_progress(steam_id_64)

    def _on_steam_login_error(self, error: str) -> None:
        """Handles Steam authentication errors.

        Args:
            error: The error message from authentication.
        """
        self.set_status(t('ui.login.status_failed'))
        self.reload_btn.show()
        UIHelper.show_error(self, error)

    # --- Main Logic ---

    def force_save(self) -> None:
        """Manually saves the VDF configuration to disk.

        Shows success status or error dialog based on save result.
        """
        if self.vdf_parser:
            if self._save_collections():
                self.set_status(t('common.success'))
            else:
                UIHelper.show_error(self, t('logs.config.save_error', error="Unknown"))

    def show_about(self) -> None:
        """Shows the About dialog with application information."""
        QMessageBox.about(self, t('ui.menu.help.about'), t('app.description'))

    def _load_data(self) -> None:
        """Performs the initial data loading sequence.

        Detects Steam path and user, initializes parsers and managers,
        and starts the game loading process.
        """
        self.set_status(t('common.loading'))

        if not config.STEAM_PATH:
            UIHelper.show_warning(self, t('logs.main.steam_not_found'))
            self.reload_btn.show()
            return

        short_id, long_id = config.get_detected_user()
        target_id = config.STEAM_USER_ID if config.STEAM_USER_ID else long_id

        if not short_id and not target_id:
            UIHelper.show_warning(self, t('ui.errors.no_users_found'))
            self.reload_btn.show()
            return

        # Restore login state if STEAM_USER_ID was saved
        if config.STEAM_USER_ID and not self.steam_username:
            self.steam_username = self._fetch_steam_persona_name(config.STEAM_USER_ID)
            self._refresh_toolbar()

        display_id = self.steam_username if self.steam_username else (target_id if target_id else short_id)
        self.user_label.setText(t('ui.main_window.user_label', user_id=display_id))

        # Initialize GameService
        self.game_service = GameService(
            str(config.STEAM_PATH),
            config.STEAM_API_KEY,
            str(config.CACHE_DIR)
        )

        # Initialize parsers through GameService
        config_path = config.get_localconfig_path(short_id)
        if not config_path:
            UIHelper.show_error(self, t('ui.errors.localconfig_load_error'))
            self.reload_btn.show()
            return

        vdf_success, cloud_success = self.game_service.initialize_parsers(str(config_path), short_id)

        if not vdf_success and not cloud_success:
            UIHelper.show_error(self, t('ui.errors.localconfig_load_error'))
            self.reload_btn.show()
            return

        # Set references for backward compatibility
        self.vdf_parser = self.game_service.vdf_parser
        self.cloud_storage_parser = self.game_service.cloud_storage_parser

        # Load games through GameService
        self._load_games_with_progress(target_id)

    def _load_games_with_progress(self, user_id: Optional[str]) -> None:
        """Starts game loading with a progress dialog.

        Args:
            user_id: The Steam user ID to load games for, or None for local only.
        """
        self.progress_dialog = QProgressDialog(
            t('common.loading'),
            t('common.cancel'),
            0, 100,
            self
        )
        self.progress_dialog.setWindowTitle(t('ui.main_window.status_ready'))
        self.progress_dialog.setWindowModality(Qt.WindowModality.WindowModal)
        self.progress_dialog.setMinimumDuration(0)
        self.progress_dialog.setValue(0)

        self.load_thread = GameLoadThread(self.game_service, user_id or "local")
        # noinspection PyUnresolvedReferences
        self.load_thread.progress_update.connect(self._on_load_progress)
        # noinspection PyUnresolvedReferences
        self.load_thread.finished.connect(self._on_load_finished)
        self.load_thread.start()

    def _on_load_progress(self, step: str, current: int, total: int) -> None:
        """Updates the progress dialog during game loading.

        Args:
            step: Description of the current loading step.
            current: Current progress count.
            total: Total items to process.
        """
        if self.progress_dialog:
            self.progress_dialog.setLabelText(step)
            if total > 0:
                percent = int((current / total) * 100)
                self.progress_dialog.setValue(percent)

    def _on_load_finished(self, success: bool) -> None:
        """Handles completion of the game loading process.

        Args:
            success: Whether loading completed successfully.
        """
        if self.progress_dialog:
            self.progress_dialog.close()
            self.progress_dialog = None

        # Get game_manager reference from game_service
        self.game_manager = self.game_service.game_manager if self.game_service else None

        if not success or not self.game_manager or not self.game_manager.games:
            UIHelper.show_warning(self, t('ui.errors.no_games_found'))
            self.reload_btn.show()
            self.set_status(t('common.error'))
            return

        # Merge collections using GameService
        self.game_service.merge_with_localconfig()

        # Apply metadata using GameService
        self.steam_scraper = SteamStoreScraper(config.CACHE_DIR, config.TAGS_LANGUAGE)
        self.game_service.apply_metadata()

        # Set appinfo_manager reference for backward compatibility
        self.appinfo_manager = self.game_service.appinfo_manager

        # Initialize CategoryService after parsers and game_manager are ready
        from src.services.category_service import CategoryService
        self.category_service = CategoryService(
            vdf_parser=self.vdf_parser,
            cloud_parser=self.cloud_storage_parser,
            game_manager=self.game_manager
        )

        # Initialize MetadataService after appinfo_manager is ready
        from src.services.metadata_service import MetadataService
        self.metadata_service = MetadataService(
            appinfo_manager=self.appinfo_manager,
            game_manager=self.game_manager
        )

        # Initialize AutoCategorizeService after category_service is ready
        from src.services.autocategorize_service import AutoCategorizeService
        self.autocategorize_service = AutoCategorizeService(
            game_manager=self.game_manager,
            category_service=self.category_service,
            steam_scraper=self.steam_scraper
        )

        self._populate_categories()

        status_msg = self.game_manager.get_load_source_message()
        self.set_status(status_msg)
        self.reload_btn.hide()

        # Statistik aktualisieren
        self._update_statistics()

    @staticmethod
    def _german_sort_key(text: str) -> str:
        """
        Sort key for German text with umlauts and special characters.

        Replaces German umlauts with their base letters for proper alphabetical sorting:
        Ä/ä → a, Ö/ö → o, Ü/ü → u, ß → ss

        This ensures that "Übernatürlich" comes after "Uhr" (not at the end),
        and "NIEDLICH", "Niedlich", "niedlich" appear together.

        Args:
            text: The text to create a sort key for.

        Returns:
            Normalized lowercase string for sorting.
        """
        # Map umlauts to come AFTER their base letter:
        # a < ä, o < ö, u < ü (German alphabetical order)
        replacements = {
            'ä': 'a~', 'Ä': 'a~',  # ~ comes after all letters
            'ö': 'o~', 'Ö': 'o~',
            'ü': 'u~', 'Ü': 'u~',
            'ß': 'ss'
        }
        result = text.lower()
        for old, new in replacements.items():
            result = result.replace(old, new)
        return result

    def _populate_categories(self) -> None:
        """Use cached data if available."""
        if hasattr(self, "_categories_cache") and self._categories_cache and not getattr(self, "_cache_invalidated",
                                                                                         True):
            self.tree.populate_categories(self._categories_cache)
            return

        """Refreshes the sidebar tree with current game data.

        Builds category data including All Games, Uncategorized, Hidden,
        and user-defined categories. Hidden games are excluded from normal
        categories and shown only in the Hidden category.
        """
        if not self.game_manager: return

        # Separate hidden and visible games
        all_games_raw = self.game_manager.get_real_games()  # Nur echte Spiele (ohne Proton auf Linux)
        visible_games = sorted([g for g in all_games_raw if not g.hidden], key=lambda g: g.sort_name.lower())
        hidden_games = sorted([g for g in all_games_raw if g.hidden], key=lambda g: g.sort_name.lower())

        # 1-3. Build initial categories (All, Uncategorized, Hidden)
        categories_data = {
            t('ui.categories.all_games'): visible_games,
            t('ui.categories.uncategorized'): sorted(
                [g for g in self.game_manager.get_uncategorized_games() if not g.hidden],
                key=lambda g: g.sort_name.lower()
            ),
            t('ui.categories.hidden'): hidden_games
        }

        # 4. Favorites (only visible)
        favorites = sorted([g for g in self.game_manager.get_favorites() if not g.hidden],
                           key=lambda g: g.sort_name.lower())
        if favorites:
            categories_data[t('ui.categories.favorites')] = favorites

        # 5. User categories (only visible games)
        cats = self.game_manager.get_all_categories()
        # Sort with German umlaut support: Ä→A, Ö→O, Ü→U
        for cat_name in sorted(cats.keys(), key=self._german_sort_key):
            if cat_name != 'favorite':
                cat_games = sorted([g for g in self.game_manager.get_games_by_category(cat_name) if not g.hidden],
                                   key=lambda g: g.sort_name.lower())
                if cat_games:  # Only add if there are visible games
                    categories_data[cat_name] = cat_games

        # Store in cache
        if hasattr(self, "_categories_cache"):
            self._categories_cache = categories_data
            self._cache_invalidated = False

        self.tree.populate_categories(categories_data)

    def _on_games_selected(self, games: List[Game]) -> None:
        """Handles multi-selection changes in the game tree.
        Args:
            games: List of currently selected games.
        """
        self.selected_games = games
        all_categories = list(self.game_manager.get_all_categories().keys())

        if len(games) > 1:
            # Show multi-select view in details widget
            self.set_status(t('ui.main_window.games_selected', count=len(games)))
            self.details_widget.set_games(games, all_categories)
        elif len(games) == 1:
            # Show single game view
            self.set_status(f"{games[0].name}")
            self.on_game_selected(games[0])
        else:
            # No selection - could clear the details widget
            pass

    def on_game_selected(self, game: Game) -> None:
        """Handles single game selection in the tree.

        Args:
            game: The selected game object.
        """
        # Ignore if multiple games are selected (multi-select mode)
        if len(self.selected_games) > 1:
            return

        self.selected_game = game
        all_categories = list(self.game_manager.get_all_categories().keys())

        # PERFORMANCE FIX: Show UI immediately, fetch details in background
        self.details_widget.set_game(game, all_categories)

        # Fetch details asynchronously if missing (non-blocking)
        if not game.developer or not game.proton_db_rating or not game.steam_deck_status:
            self._fetch_game_details_async(game.app_id, all_categories)

    def _fetch_game_details_async(self, app_id: str, all_categories: List[str]) -> None:
        """Fetches game details in a background thread without blocking the UI.

        This method improves performance by loading missing metadata asynchronously,
        allowing the UI to remain responsive during API calls.

        Args:
            app_id: The Steam app ID to fetch details for.
            all_categories: List of all available categories for UI update.
        """

        class FetchThread(QThread):
            """Background thread for fetching game details."""
            finished_signal = pyqtSignal(bool)

            def __init__(self, game_manager, target_app_id):
                super().__init__()
                self.game_manager = game_manager
                self.target_app_id = target_app_id

            def run(self):
                """Executes the fetch operation in background."""
                success = self.game_manager.fetch_game_details(self.target_app_id)
                self.finished_signal.emit(success)

        # Create and start background thread
        fetch_thread = FetchThread(self.game_manager, app_id)

        def on_fetch_complete(success: bool):
            """Updates UI when fetch completes."""
            if success and self.selected_game and self.selected_game.app_id == app_id:
                # Only update if this game is still selected
                game = self.game_manager.get_game(app_id)
                if game:
                    self.details_widget.set_game(game, all_categories)

        fetch_thread.finished_signal.connect(on_fetch_complete)
        fetch_thread.start()

        # Store reference to prevent garbage collection
        if not hasattr(self, '_fetch_threads'):
            self._fetch_threads = []
        self._fetch_threads.append(fetch_thread)

        # Clean up finished threads
        self._fetch_threads = [thread for thread in self._fetch_threads if thread.isRunning()]

    def _restore_game_selection(self, app_ids: List[str]) -> None:
        """Restores game selection in the tree widget after refresh.

        This method finds and re-selects games in the tree widget based on their
        app IDs. It's used to maintain the selection state after operations that
        refresh the tree (like category changes).

        Args:
            app_ids: List of Steam app IDs to select.
        """
        if not app_ids:
            return

        # Temporarily block signals to prevent triggering selection events
        self.tree.blockSignals(True)

        # Find and select the game items in the tree
        for i in range(self.tree.topLevelItemCount()):
            category_item = self.tree.topLevelItem(i)
            for j in range(category_item.childCount()):
                game_item = category_item.child(j)
                item_app_id = game_item.data(0, Qt.ItemDataRole.UserRole)
                if item_app_id and item_app_id in app_ids:
                    game_item.setSelected(True)

        # Re-enable signals
        self.tree.blockSignals(False)

        # Manually update selected_games list
        self.selected_games = [self.game_manager.get_game(aid) for aid in app_ids]
        self.selected_games = [g for g in self.selected_games if g is not None]

    def _apply_category_to_games(self, games: List[Game], category: str, checked: bool) -> None:
        """Helper method to apply category changes to a list of games.

        Args:
            games: List of games to update.
            category: The category name.
            checked: Whether to add (True) or remove (False) the category.
        """
        for game in games:
            if checked:
                if category not in game.categories:
                    game.categories.append(category)
                    self._add_app_category(game.app_id, category)
            else:
                if category in game.categories:
                    game.categories.remove(category)
                    self._remove_app_category(game.app_id, category)

    def _on_category_changed_from_details(self, app_id: str, category: str, checked: bool) -> None:
        """Handles category toggle events from the details widget.

        Supports both single and multi-selection. If multiple games are selected,
        the category change is applied to all selected games.

        Args:
            app_id: The Steam app ID of the game (ignored for multi-select).
            category: The category name being toggled.
            checked: Whether the category should be added or removed.
        """
        if not self.vdf_parser:
            return

        # Prevent multiple refreshes during rapid checkbox events
        if hasattr(self, '_in_batch_update') and self._in_batch_update:
            # Just update data, skip UI refresh
            games_to_update = []
            if len(self.selected_games) > 1:
                games_to_update = self.selected_games
            else:
                game = self.game_manager.get_game(app_id)
                if game:
                    games_to_update = [game]

            self._apply_category_to_games(games_to_update, category, checked)
            return

        # Set batch flag
        self._in_batch_update = True

        # Determine which games to update
        games_to_update = []
        if len(self.selected_games) > 1:
            # Multi-select mode: update all selected games
            games_to_update = self.selected_games
        else:
            # Single game mode
            game = self.game_manager.get_game(app_id)
            if game:
                games_to_update = [game]

        if not games_to_update:
            return

        # Invalidate cache
        if hasattr(self, "_cache_invalidated"):
            self._cache_invalidated = True

        # Apply category change to all games
        self._apply_category_to_games(games_to_update, category, checked)

        # Schedule save (batched with 100ms delay)
        self._schedule_save()

        # Save the current selection before refreshing
        selected_app_ids = [game.app_id for game in self.selected_games]

        # If search is active, re-run the search instead of showing all categories
        if self.current_search_query:
            self.on_search(self.current_search_query)
        else:
            self._populate_categories()

        # Restore the selection
        if selected_app_ids:
            self._restore_game_selection(selected_app_ids)

        all_categories = list(self.game_manager.get_all_categories().keys())

        # Refresh details widget
        if len(self.selected_games) > 1:
            # Multi-select: refresh the multi-select view
            self.details_widget.set_games(self.selected_games, all_categories)
        elif len(self.selected_games) == 1:
            # Single select: refresh single game view
            self.details_widget.set_game(self.selected_games[0], all_categories)

        # Reset batch flag after 500ms to allow next batch
        QTimer.singleShot(500, lambda: setattr(self, '_in_batch_update', False))

    def _on_games_dropped(self, games: List[Game], target_category: str) -> None:
        """
        Handles drag-and-drop of games onto a category.

        Updates the game categories in memory and persists changes to the VDF file.

        Args:
            games: List of games that were dropped.
            target_category: The category they were dropped onto.
        """
        if not self.vdf_parser:
            return

        for game in games:
            # Add to target category if not already there
            if target_category not in game.categories:
                game.categories.append(target_category)
                self._add_app_category(game.app_id, target_category)

        # Save changes to VDF file
        self._save_collections()

        # Refresh the tree - maintain search if active
        if self.current_search_query:
            self.on_search(self.current_search_query)
        else:
            self._populate_categories()

        # Update details widget if one of the dropped games is currently selected
        if games and self.details_widget.current_game and self.details_widget.current_game.app_id in [g.app_id for g in
                                                                                                      games]:
            all_categories = list(self.game_manager.get_all_categories().keys())
            self.details_widget.set_game(self.details_widget.current_game, all_categories)

    def on_game_right_click(self, game: Game, pos) -> None:
        """Shows context menu for a right-clicked game.

        Args:
            game: The game that was right-clicked.
            pos: The screen position for the context menu.
        """
        menu = QMenu(self)

        menu.addAction(t('ui.context_menu.view_details'), lambda: self.on_game_selected(game))
        menu.addAction(t('ui.context_menu.toggle_favorite'), lambda: self.toggle_favorite(game))

        menu.addSeparator()

        if hasattr(game, 'hidden'):
            if game.hidden:
                menu.addAction(t('ui.context_menu.unhide_game'), lambda: self.toggle_hide_game(game, False))
            else:
                menu.addAction(t('ui.context_menu.hide_game'), lambda: self.toggle_hide_game(game, True))

        menu.addAction(t('ui.context_menu.remove_from_local'), lambda: self.remove_from_local_config(game))
        menu.addAction(t('ui.context_menu.remove_from_account'), lambda: self.remove_game_from_account(game))

        menu.addSeparator()
        menu.addAction(t('ui.context_menu.open_store'), lambda: self.open_in_store(game))
        menu.addAction(t('ui.context_menu.check_store'), lambda: self.check_store_availability(game))
        menu.addSeparator()

        # Auto-categorize (for single or multiple games)
        if len(self.selected_games) > 1:
            menu.addAction(t('ui.menu.edit.auto_categorize'), self.auto_categorize_selected)
        else:
            menu.addAction(t('ui.menu.edit.auto_categorize'), lambda: self.auto_categorize_single(game))

        menu.addSeparator()
        menu.addAction(t('ui.context_menu.edit_metadata'), lambda: self.edit_game_metadata(game))
        menu.exec(pos)

    def on_category_right_click(self, category: str, pos) -> None:
        """Shows context menu for a right-clicked category.

        Args:
            category: The category name that was right-clicked (or "__MULTI__" for multi-select).
            pos: The screen position for the context menu.
        """
        menu = QMenu(self)

        # Handle multi-category selection
        if category == "__MULTI__":
            selected_categories = self.tree.get_selected_categories()
            if len(selected_categories) > 1:
                menu.addAction(t('ui.context_menu.merge_categories'),
                               lambda: self.merge_categories(selected_categories))
                menu.addSeparator()
                menu.addAction(t('ui.context_menu.delete'),
                               lambda: self.delete_multiple_categories(selected_categories))
            menu.exec(pos)
            return

        # Single category
        if category == t('ui.categories.favorites'):
            return

        special_cats = [t('ui.categories.all_games'), t('ui.categories.uncategorized')]

        if category in special_cats:
            menu.addAction(t('ui.context_menu.create_collection'), self.create_new_collection)
            menu.addSeparator()
            menu.addAction(t('ui.menu.edit.auto_categorize'), lambda: self.auto_categorize_category(category))
        else:
            menu.addAction(t('ui.context_menu.create_collection'), self.create_new_collection)
            menu.addSeparator()
            menu.addAction(t('ui.context_menu.rename'), lambda: self.rename_category(category))
            menu.addAction(t('ui.context_menu.delete'), lambda: self.delete_category(category))
            menu.addSeparator()
            menu.addAction(t('ui.menu.edit.auto_categorize'), lambda: self.auto_categorize_category(category))

        menu.exec(pos)

    def toggle_hide_game(self, game: Game, hide: bool) -> None:
        """Toggles the hidden status of a game.

        Args:
            game: The game to hide or unhide.
            hide: True to hide the game, False to show it.
        """
        if not self.vdf_parser: return
        self.vdf_parser.set_app_hidden(game.app_id, hide)

        if self._save_collections():
            game.hidden = hide

            # Refresh UI
            self._populate_categories()

            status_word = t('ui.visibility.hidden') if hide else t('ui.visibility.visible')
            self.set_status(f"{status_word}: {game.name}")

            msg = t('ui.visibility.message', game=game.name, status=status_word)
            UIHelper.show_success(self, msg, t('ui.visibility.title'))

    def remove_from_local_config(self, game: Game) -> None:
        """Removes a game entry from the local Steam configuration.

        This is useful for removing 'ghost' entries that no longer exist in Steam
        but still appear in localconfig.vdf.

        Args:
            game: The game to remove from the local configuration.
        """
        if not UIHelper.confirm(
                self,
                t('ui.dialogs.remove_local_warning', game=game.name),
                t('ui.dialogs.remove_local_title')
        ):
            return

        if self.vdf_parser:
            success = self.vdf_parser.remove_app(str(game.app_id))
            if success:
                self._save_collections()
                # Remove from game manager
                if self.game_manager and str(game.app_id) in self.game_manager.games:
                    del self.game_manager.games[str(game.app_id)]
                # Refresh tree
                self._populate_categories()
                UIHelper.show_success(self, t('ui.dialogs.remove_local_success', game=game.name), t('common.success'))
            else:
                UIHelper.show_error(self, t('ui.dialogs.remove_local_error'))

    def remove_game_from_account(self, game: Game) -> None:
        """Redirects the user to Steam Support to remove a game from their account.

        Shows a warning dialog before opening the browser.

        Args:
            game: The game to remove from the account.
        """
        if UIHelper.confirm(
                self,
                t('ui.dialogs.remove_account_warning'),
                t('ui.dialogs.remove_account_title')
        ):
            import webbrowser
            # Steam Support URL for removing a game (issueid 123 is "remove from account")
            url = f"https://help.steampowered.com/en/wizard/HelpWithGameIssue/?appid={game.app_id}&issueid=123"
            webbrowser.open(url)

    def on_search(self, query: str) -> None:
        """Filters the game tree based on search query.

        Args:
            query: The search string to filter games by name.
        """
        self.current_search_query = query  # Save current search

        if not query:
            self._populate_categories()
            return
        if not self.game_manager: return
        results = [g for g in self.game_manager.get_real_games() if query.lower() in g.name.lower()]

        if results:
            cat_name = t('ui.search.results_category', count=len(results))
            sorted_results = sorted(results, key=lambda g: g.name.lower())
            self.tree.populate_categories({cat_name: sorted_results})
            self.tree.expandAll()
            self.set_status(t('ui.search.status_found', count=len(results)))
        else:
            self.tree.clear()
            self.set_status(t('ui.search.status_none'))

    def clear_search(self) -> None:
        """Clears the search field and restores the full category view."""
        self.current_search_query = ""  # Clear search state
        self.search_entry.clear()
        self._populate_categories()

    def toggle_favorite(self, game: Game) -> None:
        """Toggles the favorite status of a game.

        Args:
            game: The game to add to or remove from favorites.
        """
        if not self.vdf_parser: return
        if game.is_favorite():
            if 'favorite' in game.categories: game.categories.remove('favorite')
            self._remove_app_category(game.app_id, 'favorite')
        else:
            if 'favorite' not in game.categories: game.categories.append('favorite')
            self._add_app_category(game.app_id, 'favorite')

        self._save_collections()
        self._populate_categories()

    @staticmethod
    def open_in_store(game: Game) -> None:
        """Opens the Steam Store page for a game in the default browser.

        Args:
            game: The game to view in the store.
        """
        import webbrowser
        webbrowser.open(f"https://store.steampowered.com/app/{game.app_id}")

    def check_store_availability(self, game: Game) -> None:
        """Checks if a game is still available on the Steam Store.

        Performs an HTTP request to the store page and reports the result
        based on status code and response content.

        Args:
            game: The game to check availability for.
        """
        progress = QProgressDialog(t('ui.store_check.checking'), None, 0, 0, self)
        progress.setWindowModality(Qt.WindowModality.WindowModal)
        progress.setWindowTitle(t('ui.store_check.title'))
        progress.show()
        QApplication.processEvents()

        class StoreCheckThread(QThread):
            finished = pyqtSignal(str, str)

            def __init__(self, app_id: str):
                super().__init__()
                self.app_id = app_id

            def run(self):
                try:
                    url = f"https://store.steampowered.com/app/{self.app_id}/"
                    response = requests.get(url, timeout=10, allow_redirects=False, headers={'User-Agent': 'SLM/1.0'})

                    if response.status_code == 200:
                        text_lower = response.text.lower()

                        # Check for geo-blocking (works for both English and German)
                        if ('not available in your country' in text_lower or
                                'nicht in ihrem land' in text_lower or
                                'not available in your region' in text_lower or
                                'currently not available' in text_lower):
                            self.finished.emit('geo_locked', t('ui.store_check.geo_locked'))
                        # Check if redirected to age gate
                        elif 'agecheck' in text_lower:
                            self.finished.emit('age_gate', t('ui.store_check.age_gate'))
                        # Check if app page exists
                        elif 'app_header' in text_lower or 'game_area_purchase' in text_lower:
                            self.finished.emit('available', t('ui.store_check.available'))
                        else:
                            # Page loaded but doesn't look like a valid store page
                            self.finished.emit('delisted', t('ui.store_check.delisted'))
                    elif response.status_code == 302:
                        # Follow redirect to check if it's age gate or delisted
                        redirect_url = response.headers.get('Location', '')
                        if 'agecheck' in redirect_url:
                            self.finished.emit('age_gate', t('ui.store_check.age_gate'))
                        else:
                            self.finished.emit('delisted', t('ui.store_check.delisted'))
                    elif response.status_code in [404, 403]:
                        self.finished.emit('delisted', t('ui.store_check.removed'))
                    else:
                        self.finished.emit('unknown', t('ui.store_check.unknown', code=response.status_code))

                except Exception as ex:
                    self.finished.emit('unknown', str(ex))

        def on_check_finished(status: str, details: str):
            progress.close()
            title = t('ui.store_check.title')
            msg = f"{game.name}: {details}"

            if status == 'available':
                UIHelper.show_success(self, msg, title)
            elif status == 'age_gate':
                UIHelper.show_info(self, msg, title)
            else:
                UIHelper.show_warning(self, msg, title)

        self.store_check_thread = StoreCheckThread(game.app_id)
        # noinspection PyUnresolvedReferences
        self.store_check_thread.finished.connect(on_check_finished)
        self.store_check_thread.start()

    def remove_duplicate_collections(self) -> None:
        """
        Remove duplicate collections using CategoryService.

        Identifies collections with identical names but different app counts,
        keeping only the collection that matches the expected count from the
        game manager. Shows error if cloud storage is not available.

        Note:
            Only available when cloud storage parser is active.
        """
        if not self.category_service:
            return

        # Show confirmation dialog
        message = t('ui.main_window.remove_duplicates_confirm')
        if not UIHelper.confirm(self, message, t('ui.main_window.remove_duplicates_title')):
            return

        try:
            removed = self.category_service.remove_duplicate_collections()

            if removed > 0:
                self._save_collections()
                self._populate_categories()
                UIHelper.show_success(self, t('ui.main_window.duplicates_removed', count=removed))
            else:
                UIHelper.show_info(self, t('ui.main_window.no_duplicates'))
        except RuntimeError as e:
            UIHelper.show_error(self, str(e))

    def create_new_collection(self) -> None:
        """
        Create a new empty collection using CategoryService.

        Prompts the user for a collection name and creates a new empty collection
        in the active parser (cloud storage or localconfig). Validates that the
        name doesn't already exist before creating.

        Note:
            Uses CategoryService which handles parser selection automatically.
        """
        if not self.category_service:
            return

        name, ok = UIHelper.ask_text(
            self,
            t('ui.main_window.create_collection_title'),
            t('ui.main_window.create_collection_prompt')
        )

        if ok and name:
            try:
                self.category_service.create_collection(name)
                self._save_collections()
                self._populate_categories()
                UIHelper.show_success(self, t('ui.main_window.collection_created', name=name))
            except ValueError as e:
                UIHelper.show_error(self, str(e))

    def rename_category(self, old_name: str) -> None:
        """Prompts the user to rename a category using CategoryService.

        Args:
            old_name: The current name of the category to rename.
        """
        if not self.category_service:
            return

        new_name, ok = UIHelper.ask_text(
            self,
            t('ui.categories.rename_title'),
            t('ui.categories.rename_msg', old=old_name)
        )

        if ok and new_name and new_name != old_name:
            try:
                self.category_service.rename_category(old_name, new_name)
                self._save_collections()
                self._populate_categories()
                self._update_statistics()
            except ValueError as e:
                UIHelper.show_error(self, str(e))

    def delete_category(self, category: str) -> None:
        """Prompts the user to delete a category using CategoryService.

        Args:
            category: The name of the category to delete.
        """
        if not self.category_service:
            return

        if UIHelper.confirm(
                self,
                t('ui.categories.delete_msg', category=category),
                t('ui.categories.delete_title')
        ):
            self.category_service.delete_category(category)
            self._save_collections()
            self._populate_categories()
            self._update_statistics()

    def delete_multiple_categories(self, categories: List[str]) -> None:
        """Prompts the user to delete multiple categories using CategoryService.

        Args:
            categories: List of category names to delete.
        """
        if not self.category_service or not categories:
            return

        # Create confirmation message
        category_list = "\n• ".join(categories)
        message: str = t('ui.categories.delete_multiple_msg', count=len(categories), category_list=f"• {category_list}")

        if UIHelper.confirm(self, message, t('ui.categories.delete_title')):
            self.category_service.delete_multiple_categories(categories)
            self._save_collections()
            self._populate_categories()
            self._update_statistics()

    def merge_categories(self, categories: List[str]) -> None:
        """
        Merges multiple categories into one using CategoryService.

        Shows a dialog to select the target category, then moves all games
        from the other categories into the target and deletes the source categories.

        Args:
            categories: List of category names to merge.
        """
        if not self.category_service or len(categories) < 2:
            return

        # Show selection dialog
        from PyQt6.QtWidgets import QDialog, QVBoxLayout, QLabel, QListWidget, QDialogButtonBox

        dialog = QDialog(self)
        dialog.setWindowTitle(t('ui.categories.merge_title'))
        dialog.setMinimumWidth(400)

        layout = QVBoxLayout()

        # Instruction label
        label = QLabel(t('ui.categories.merge_instruction', count=len(categories)))
        label.setWordWrap(True)
        layout.addWidget(label)

        # List of categories
        list_widget = QListWidget()
        for cat in sorted(categories):
            list_widget.addItem(cat)
        list_widget.setCurrentRow(0)
        layout.addWidget(list_widget)

        # Buttons
        # noinspection PyTypeChecker
        buttons = QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        button_box = QDialogButtonBox(buttons)
        button_box.accepted.connect(dialog.accept)
        button_box.rejected.connect(dialog.reject)
        layout.addWidget(button_box)

        dialog.setLayout(layout)

        if dialog.exec() == QDialog.DialogCode.Accepted:
            selected_item = list_widget.currentItem()
            if not selected_item:
                return

            target_category = selected_item.text()
            source_categories = [cat for cat in categories if cat != target_category]

            # Use CategoryService to merge
            self.category_service.merge_categories(source_categories, target_category)
            self._save_collections()
            self._populate_categories()

            # Show success message
            UIHelper.show_success(
                self,
                t('ui.categories.merge_success', target=target_category, count=len(source_categories)),
                t('ui.categories.merge_title')
            )

    def auto_categorize(self) -> None:
        """Opens the auto-categorize dialog for selected or uncategorized games."""
        if self.selected_games:
            self._show_auto_categorize_dialog(self.selected_games, None)
        else:
            self._show_auto_categorize_dialog(self.game_manager.get_uncategorized_games(), None)

    def auto_categorize_selected(self) -> None:
        """Opens the auto-categorize dialog for currently selected games."""
        if self.selected_games: self._show_auto_categorize_dialog(self.selected_games, None)

    def auto_categorize_single(self, game: Game) -> None:
        """Opens the auto-categorize dialog for a single game.

        Args:
            game: The game to auto-categorize.
        """
        self._show_auto_categorize_dialog([game], None)

    def auto_categorize_category(self, category: str) -> None:
        """Opens the auto-categorize dialog for games in a specific category.

        Args:
            category: The category name to auto-categorize.
        """
        if category == t('ui.categories.all_games'):
            self._show_auto_categorize_dialog(self.game_manager.get_real_games(), category)
        elif category == t('ui.categories.uncategorized'):
            self._show_auto_categorize_dialog(self.game_manager.get_uncategorized_games(), category)
        else:
            self._show_auto_categorize_dialog(self.game_manager.get_games_by_category(category), category)

    def _show_auto_categorize_dialog(self, games: List[Game], category_name: Optional[str]) -> None:
        """Shows the auto-categorize dialog with the specified games.

        Args:
            games: List of games to potentially categorize.
            category_name: Optional name of the source category.
        """
        self.dialog_games = games
        if not self.game_manager:
            return

        # Create dialog with callback that checks cache BEFORE closing
        dialog = AutoCategorizeDialog(
            self,
            games,
            len(self.game_manager.games),
            lambda settings: self._check_and_start(settings, dialog),
            category_name
        )
        dialog.exec()

    def _check_and_start(self, settings: dict, dialog: 'AutoCategorizeDialog') -> None:
        """
        Check cache coverage before starting auto-categorization.

        This method is called when user clicks "Start" in the dialog.
        Dialog stays open until cache check is complete.

        Args:
            settings: Auto-categorize settings from dialog.
            dialog: The AutoCategorizeDialog instance (to close it later).
        """
        # Check if tags method is selected
        if 'tags' not in settings.get('methods', []):
            # No tags, no cache check needed
            dialog.accept()
            self._do_auto_categorize(settings)
            return

        # Tags selected - check cache coverage
        if not self.steam_scraper or not self.game_manager:
            dialog.accept()
            self._do_auto_categorize(settings)
            return

        # Get the RIGHT games based on user's choice!
        if settings['scope'] == 'all':
            actual_games = self.game_manager.get_real_games()
        else:
            actual_games = self.dialog_games

        # Check cache coverage with ACTUAL games using AutoCategorizeService
        coverage = self.autocategorize_service.get_cache_coverage(actual_games)

        # If more than 50% is cached, no warning needed
        if coverage['percentage'] >= 50:
            dialog.accept()
            self._do_auto_categorize(settings)
            return

        # Low cache coverage - show warning
        missing = coverage['missing']
        time_str = self.autocategorize_service.estimate_time(missing)

        # Show warning dialog (ON TOP of AutoCategorizeDialog)
        msg_box = QMessageBox(self)
        msg_box.setIcon(QMessageBox.Icon.Warning)
        msg_box.setWindowTitle(t('ui.auto_categorize.cache_warning_title'))
        msg_box.setText(t('ui.auto_categorize.cache_warning_message',
                          cached=coverage['cached'],
                          total=coverage['total'],
                          time=time_str))

        # Custom buttons
        yes_button = msg_box.addButton(t('common.yes'), QMessageBox.ButtonRole.YesRole)
        no_button = msg_box.addButton(t('common.no'), QMessageBox.ButtonRole.NoRole)
        msg_box.setDefaultButton(no_button)

        msg_box.exec()

        if msg_box.clickedButton() == yes_button:
            # User wants to continue
            dialog.accept()
            self._do_auto_categorize(settings)
        # else: User cancelled - dialog stays open

    def _do_auto_categorize(self, settings: dict) -> None:
        """Executes the auto-categorization process with the given settings.

        Args:
            settings: Dictionary containing scope, methods, and tags_count options.
        """
        if not settings or not self.vdf_parser: return

        games = self.game_manager.get_real_games() if settings['scope'] == 'all' else self.dialog_games
        methods = settings['methods']

        progress = QProgressDialog(
            t('ui.auto_categorize.processing', current=0, total=len(games)),
            t('common.cancel'), 0, len(methods) * len(games), self
        )
        progress.setWindowModality(Qt.WindowModality.WindowModal)

        step = 0
        for method in methods:
            if progress.wasCanceled():
                break

            if method == 'tags':
                # Progress callback for tags
                def tags_progress(index, name):
                    if progress.wasCanceled():
                        return
                    progress.setValue(step + index)
                    if index % 10 == 0:
                        progress.setLabelText(t('ui.auto_categorize.status_tags', game=name[:30]))
                    QApplication.processEvents()

                self.autocategorize_service.categorize_by_tags(
                    games,
                    tags_count=settings['tags_count'],
                    progress_callback=tags_progress
                )
                step += len(games)

            elif method == 'publisher':
                for i in range(len(games)):
                    if progress.wasCanceled():
                        break
                    progress.setValue(step + i)
                self.autocategorize_service.categorize_by_publisher(games)
                step += len(games)

            elif method == 'franchise':
                for i in range(len(games)):
                    if progress.wasCanceled():
                        break
                    progress.setValue(step + i)
                self.autocategorize_service.categorize_by_franchise(games)
                step += len(games)

            elif method == 'genre':
                for i in range(len(games)):
                    if progress.wasCanceled():
                        break
                    progress.setValue(step + i)
                self.autocategorize_service.categorize_by_genre(games)
                step += len(games)

        self._save_collections()
        progress.close()
        self._populate_categories()
        UIHelper.show_success(self, t('common.success'))

    def _on_pegi_override_requested(self, app_id: str, rating: str) -> None:
        """Handle PEGI override request from details widget.

        Args:
            app_id: The app ID of the game.
            rating: The selected PEGI rating (e.g., "18") or empty string to remove override.
        """
        if not self.appinfo_manager:
            return

        # Save override
        if rating:  # Set override
            self.appinfo_manager.set_app_metadata(app_id, {'pegi_rating': rating})
            self.appinfo_manager.save_appinfo()
            UIHelper.show_success(self, t('ui.pegi_selector.saved', rating=rating))
        else:  # Remove override
            if app_id in self.appinfo_manager.modifications:
                if 'pegi_rating' in self.appinfo_manager.modifications[app_id].get('modified', {}):
                    del self.appinfo_manager.modifications[app_id]['modified']['pegi_rating']
                    self.appinfo_manager.save_appinfo()
                    UIHelper.show_success(self, t('ui.pegi_selector.removed'))

        # Reload game to show new rating
        game = self.game_manager.get_game(app_id)
        if game:
            # Apply override to game object
            if rating:
                game.pegi_rating = rating
            else:
                # Restore original from Steam API
                original = self.appinfo_manager.modifications.get(app_id, {}).get('original', {})
                game.pegi_rating = original.get('pegi_rating', '')

            self.on_game_selected(game)

    def edit_game_metadata(self, game: Game) -> None:
        """Opens the metadata edit dialog for a single game using MetadataService.

        Args:
            game: The game to edit metadata for.
        """
        if not self.metadata_service:
            return

        meta = self.metadata_service.get_game_metadata(game.app_id, game)
        original_meta = self.metadata_service.get_original_metadata(game.app_id, meta.copy())

        dialog = MetadataEditDialog(self, game.name, meta, original_meta)

        if dialog.exec():
            new_meta = dialog.get_metadata()
            if new_meta:
                write_vdf = new_meta.pop('write_to_vdf', False)
                self.metadata_service.set_game_metadata(game.app_id, new_meta)

                if write_vdf:
                    self.appinfo_manager.load_appinfo()
                    self.appinfo_manager.write_to_vdf(backup=True)

                if new_meta.get('name'):
                    game.name = new_meta['name']

                self._populate_categories()
                self.on_game_selected(game)
                UIHelper.show_success(self, t('ui.metadata_editor.updated_single', game=game.name))

    def bulk_edit_metadata(self) -> None:
        """Opens the bulk metadata edit dialog for selected games using MetadataService."""
        if not self.selected_games or not self.metadata_service:
            UIHelper.show_warning(self, t('ui.errors.no_selection'))
            return

        game_names = [g.name for g in self.selected_games]
        dialog = BulkMetadataEditDialog(self, len(self.selected_games), game_names)

        if dialog.exec():
            settings = dialog.get_metadata()
            if settings:
                name_mods = settings.pop('name_modifications', None)
                count = self.metadata_service.apply_bulk_metadata(
                    self.selected_games,
                    settings,
                    name_mods
                )
                self._populate_categories()
                UIHelper.show_success(self, t('ui.metadata_editor.updated_bulk', count=count))

    def find_missing_metadata(self) -> None:
        """Shows a dialog listing games with incomplete metadata using MetadataService."""
        if not self.metadata_service:
            return

        affected = self.metadata_service.find_missing_metadata()

        if affected:
            dialog = MissingMetadataDialog(self, affected)
            dialog.exec()
        else:
            UIHelper.show_success(self, t('ui.tools.missing_metadata.all_complete'))

    def restore_metadata_changes(self) -> None:
        """Opens the metadata restore dialog to revert modifications using MetadataService."""
        if not self.metadata_service:
            return

        mod_count = self.metadata_service.get_modification_count()
        if mod_count == 0:
            UIHelper.show_success(self, t('ui.metadata_editor.no_changes_to_restore'))
            return

        dialog = MetadataRestoreDialog(self, mod_count)
        if dialog.exec() and dialog.should_restore():
            try:
                restored = self.metadata_service.restore_modifications()
                if restored > 0:
                    UIHelper.show_success(self, t('ui.metadata_editor.restored_count', count=restored))
                    self.refresh_data()
            except Exception as e:
                UIHelper.show_error(self, str(e))

    def refresh_data(self) -> None:
        """Reloads all game data from scratch."""
        self._load_data()

    def _show_vdf_merger(self) -> None:
        """Opens the VDF merger dialog for transferring categories between platforms."""
        dialog = VdfMergerDialog(self)
        dialog.exec()

    def show_settings(self) -> None:
        """Opens the settings dialog."""
        dialog = SettingsDialog(self)
        # noinspection PyUnresolvedReferences
        dialog.language_changed.connect(self._on_ui_language_changed_live)
        if dialog.exec():
            settings = dialog.get_settings()
            if settings: self._apply_settings(settings)

    def _on_ui_language_changed_live(self, new_language: str) -> None:
        """Handles live language change from settings dialog.

        Args:
            new_language: The new language code (e.g., 'en', 'de').
        """
        config.UI_LANGUAGE = new_language
        init_i18n(new_language)
        self._refresh_menubar()
        self._refresh_toolbar()
        self.setWindowTitle(t('ui.main_window.title'))
        self.set_status(t('ui.main_window.status_ready'))

    def _refresh_menubar(self) -> None:
        """Rebuilds menu bar after language change.

        Only clears and rebuilds the menu bar via MenuBuilder.
        The toolbar and central widget are untouched here;
        toolbar refresh is handled separately by the caller.
        """
        self.menuBar().clear()
        self.menu_builder.build(self.menuBar())
        self.user_label = self.menu_builder.user_label

    def _apply_settings(self, settings: dict) -> None:
        """Applies settings from the settings dialog.

        Args:
            settings: Dictionary containing all settings values.
        """
        config.UI_LANGUAGE = settings['ui_language']
        config.TAGS_LANGUAGE = settings['tags_language']
        config.TAGS_PER_GAME = settings['tags_per_game']
        config.IGNORE_COMMON_TAGS = settings['ignore_common_tags']
        config.STEAMGRIDDB_API_KEY = settings['steamgriddb_api_key']
        config.MAX_BACKUPS = settings['max_backups']
        if settings.get('steam_api_key'): config.STEAM_API_KEY = settings['steam_api_key']
        if settings['steam_path']: config.STEAM_PATH = Path(settings['steam_path'])
        if self.steam_scraper: self.steam_scraper.set_language(config.TAGS_LANGUAGE)

        self._save_settings(settings)
        UIHelper.show_success(self, t('ui.settings.saved'))

    @staticmethod
    def _save_settings(settings: dict) -> None:
        """Saves settings to the settings JSON file.

        Args:
            settings: Dictionary containing all settings values.
        """
        import json
        settings_file = config.DATA_DIR / 'settings.json'
        data = {
            'ui_language': settings['ui_language'],
            'tags_language': settings['tags_language'],
            'tags_per_game': settings['tags_per_game'],
            'ignore_common_tags': settings['ignore_common_tags'],
            'steamgriddb_api_key': settings['steamgriddb_api_key'],
            'steam_api_key': settings.get('steam_api_key', ''),
            'max_backups': settings['max_backups']
        }
        with open(settings_file, 'w') as f:
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
            'ui.main_window.statistics',
            category_count=stats['category_count'],
            games_in_categories=stats['games_in_categories'],
            total_games=stats['total_games']
        )

        self.stats_label.setText(stats_text)

    def closeEvent(self, event) -> None:
        """Handle window close event and check for unsaved changes.

        Args:
            event: The close event from Qt.
        """
        # Check if there are unsaved changes
        parser = self._get_active_parser()
        if parser and parser.modified:
            reply = QMessageBox.question(
                self,
                t('ui.menu.file.unsaved_changes_title'),
                t('ui.menu.file.unsaved_changes_msg'),
                QMessageBox.StandardButton.Save |
                QMessageBox.StandardButton.Discard |
                QMessageBox.StandardButton.Cancel,
                QMessageBox.StandardButton.Save
            )

            if reply == QMessageBox.StandardButton.Save:
                # Save and close
                if self._save_collections():
                    event.accept()
                else:
                    # Save failed, ask if they want to close anyway
                    retry = QMessageBox.warning(
                        self,
                        t('ui.menu.file.save_failed_title'),
                        t('ui.menu.file.save_failed_msg'),
                        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                        QMessageBox.StandardButton.No
                    )
                    if retry == QMessageBox.StandardButton.Yes:
                        event.accept()
                    else:
                        event.ignore()
            elif reply == QMessageBox.StandardButton.Discard:
                # Close without saving
                event.accept()
            else:
                # Cancel - stay open
                event.ignore()
        else:
            # No unsaved changes, close normally
            event.accept()

    # ========== Parser Wrapper Methods ==========

    def _get_active_parser(self):
        """Get the active parser (cloud storage or localconfig)."""
        return self.cloud_storage_parser if self.cloud_storage_parser else self.vdf_parser

    def _schedule_save(self) -> None:
        """Schedule a delayed save to batch multiple operations.

        Uses a 100ms timer to batch multiple rapid changes into a single save operation.
        This prevents excessive backups when performing bulk operations.
        """
        if hasattr(self, '_save_timer') and self._save_timer.isActive():
            self._save_timer.stop()

        self._save_timer = QTimer()
        self._save_timer.setSingleShot(True)
        self._save_timer.timeout.connect(self._save_collections)
        self._save_timer.start(100)  # 100ms delay

    def _save_collections(self) -> bool:
        """Save collections using the active parser."""
        # Only save to the active parser (cloud storage OR localconfig, not both!)
        if self.cloud_storage_parser:
            return self.cloud_storage_parser.save()
        elif self.vdf_parser:
            return self.vdf_parser.save()
        return False

    def _add_app_category(self, app_id: str, category: str):
        """Add category to app using CategoryService."""
        if self.category_service:
            self.category_service.add_app_to_category(app_id, category)

    def _remove_app_category(self, app_id: str, category: str):
        """Remove category from app using CategoryService."""
        if self.category_service:
            self.category_service.remove_app_from_category(app_id, category)

    def _rename_category(self, old_name: str, new_name: str):
        """Rename category using CategoryService."""
        if self.category_service:
            try:
                self.category_service.rename_category(old_name, new_name)
            except ValueError as e:
                UIHelper.show_error(self, str(e))

    def _delete_category(self, category: str):
        """Delete category using CategoryService."""
        if self.category_service:
            self.category_service.delete_category(category)

    def keyPressEvent(self, event):
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
                self.set_status(t('ui.main_window.status_ready'))
        else:
            # Pass other keys to parent
            super().keyPressEvent(event)