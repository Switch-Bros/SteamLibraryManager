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
    QLineEdit, QPushButton, QLabel, QToolBar,
    QMessageBox, QSplitter, QProgressDialog
)
from PyQt6.QtCore import Qt, QThread, QTimer

from src.config import config
from src.core.game_manager import GameManager, Game
from src.core.localconfig_parser import LocalConfigParser
from src.core.cloud_storage_parser import CloudStorageParser
from src.core.appinfo_manager import AppInfoManager
from src.core.steam_auth import SteamAuthManager
from src.integrations.steam_store import SteamStoreScraper
from src.services.game_service import GameService
from src.services.asset_service import AssetService
from src.services.search_service import SearchService  # <--- NEW

from src.ui.settings_dialog import SettingsDialog

# Components
from src.ui.game_details_widget import GameDetailsWidget
from src.ui.widgets.category_tree import GameTreeWidget
from src.ui.widgets.ui_helper import UIHelper

from src.utils.i18n import t, init_i18n

# Builders
from src.ui.builders import MenuBuilder, ToolbarBuilder, StatusbarBuilder, CentralWidgetBuilder

# Handlers
from src.ui.handlers import CategoryActionHandler, DataLoadHandler
from src.ui.handlers.selection_handler import SelectionHandler
from src.ui.handlers.category_change_handler import CategoryChangeHandler

# Actions
from src.ui.actions import (
FileActions, EditActions, ViewActions,
ToolsActions, SteamActions, GameActions
)

# Workers
from src.ui.workers import GameLoadWorker


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
        
        # NEW: Initialize SearchService
        self.search_service = SearchService() 

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

        # Threads & Dialogs
        self.store_check_thread: Optional[QThread] = None

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

        # UI Action Handlers (extracted category / context-menu logic)
        self.category_handler: CategoryActionHandler = CategoryActionHandler(self)
        self.selection_handler = SelectionHandler(self)
        self.category_change_handler = CategoryChangeHandler(self)
        self.data_load_handler = DataLoadHandler(self)

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

        # --- Central Widget (delegated to CentralWidgetBuilder) ---
        central_builder = CentralWidgetBuilder(self)
        widgets = central_builder.build()
        
        self.tree = widgets['tree']
        self.details_widget = widgets['details_widget']
        self.search_entry = widgets['search_entry']

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
        self.steam_username = DataLoadHandler._fetch_steam_persona_name(steam_id_64)

        # Update user label
        display_text = self.steam_username if self.steam_username else steam_id_64
        self.user_label.setText(t('ui.main_window.user_label', user_id=display_text))

        # Rebuild toolbar to show name instead of login button
        self._refresh_toolbar()

        if self.game_manager:
            self.data_load_handler.load_games_with_progress(steam_id_64)

    def _on_steam_login_error(self, error: str) -> None:
        """Handles Steam authentication errors.

        Args:
            error: The error message from authentication.
        """
        self.set_status(t('ui.login.status_failed'))
        self.reload_btn.show()
        UIHelper.show_error(self, error)

    # --- Main Logic ---

    def _load_data(self) -> None:
        """Performs the initial data loading sequence.

        Delegates to DataLoadHandler for all loading operations.
        """
        self.data_load_handler.load_data()

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
        """Refreshes the sidebar tree with current game data.

        Builds category data including All Games, Uncategorized, Hidden,
        and user-defined categories.  Hidden games are excluded from normal
        categories and shown only in the Hidden category.

        No caching: the tree is cheap to rebuild (~50 ms for 2 500 games)
        and a cache only adds invisible staleness bugs.
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

            # 5. User categories (visible games only — but empty collections stay visible)
        cats: dict[str, int] = self.game_manager.get_all_categories()

        # Merge in parser-owned collections that GameManager cannot see.
        # GameManager builds its list from game.categories only; an empty
        # collection has no games so it never appears there.  The parser is
        # the single source of truth for which collections actually exist.
        active_parser = self.cloud_storage_parser or self.vdf_parser
        if active_parser:
            for parser_cat in active_parser.get_all_categories():
                if parser_cat not in cats:
                    cats[parser_cat] = 0  # empty collection — count is zero

        # Sort with German umlaut support: Ä→A, Ö→O, Ü→U
        for cat_name in sorted(cats.keys(), key=self._german_sort_key):
            if cat_name != 'favorite':
                cat_games: list[Game] = sorted(
                    [g for g in self.game_manager.get_games_by_category(cat_name) if not g.hidden],
                    key=lambda g: g.sort_name.lower()
                )
                # Always add — empty collections must stay visible as "Name (0)"
                categories_data[cat_name] = cat_games

        self.tree.populate_categories(categories_data)

    def _on_games_selected(self, games: List[Game]) -> None:
        """Handles multi-selection changes. Delegated to SelectionHandler."""
        self.selection_handler.on_games_selected(games)

    def on_game_selected(self, game: Game) -> None:
        """Handles single game selection. Delegated to SelectionHandler."""
        self.selection_handler.on_game_selected(game)

    def _fetch_game_details_async(self, app_id: str, all_categories: List[str]) -> None:
        """Fetches game details async. Delegated to SelectionHandler."""
        self.selection_handler._fetch_game_details_async(app_id, all_categories)

    def _restore_game_selection(self, app_ids: List[str]) -> None:
        """Restores game selection. Delegated to SelectionHandler."""
        self.selection_handler.restore_game_selection(app_ids)

    def _apply_category_to_games(self, games: List[Game], category: str, checked: bool) -> None:
        """Applies category changes. Delegated to CategoryChangeHandler."""
        self.category_change_handler.apply_category_to_games(games, category, checked)

    def _on_category_changed_from_details(self, app_id: str, category: str, checked: bool) -> None:
        """Handles category toggles. Delegated to CategoryChangeHandler."""
        self.category_change_handler.on_category_changed_from_details(app_id, category, checked)

    def _on_games_dropped(self, games: List[Game], target_category: str) -> None:
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

    def create_new_collection(self) -> None:
        """Creates a new empty collection. Delegated to CategoryActionHandler."""
        self.category_handler.create_new_collection()

    def rename_category(self, old_name: str) -> None:
        """Renames a category. Delegated to CategoryActionHandler.

        Args:
            old_name: The current name of the category to rename.
        """
        self.category_handler.rename_category(old_name)

    def delete_category(self, category: str) -> None:
        """Deletes a single category. Delegated to CategoryActionHandler.

        Args:
            category: The name of the category to delete.
        """
        self.category_handler.delete_category(category)

    def delete_multiple_categories(self, categories: List[str]) -> None:
        """Deletes multiple categories. Delegated to CategoryActionHandler.

        Args:
            categories: List of category names to delete.
        """
        self.category_handler.delete_multiple_categories(categories)

    def merge_categories(self, categories: List[str]) -> None:
        """Merges multiple categories into one. Delegated to CategoryActionHandler.

        Args:
            categories: List of category names to merge.
        """
        self.category_handler.merge_categories(categories)

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
        parser = self._get_active_parser()
        if not parser or not parser.modified:
            # No unsaved changes — close immediately
            event.accept()
            return

        # --- 3-button dialog: Speichern / Verwerfen / Abbrechen ---
        # Manual buttons — StandardButtons werden auf Linux ohne .qm englisch angezeigt
        msg = QMessageBox(self)
        msg.setIcon(QMessageBox.Icon.Question)
        msg.setWindowTitle(t('ui.menu.file.unsaved_changes_title'))
        msg.setText(t('ui.menu.file.unsaved_changes_msg'))

        save_btn    = msg.addButton(t('common.save'),    QMessageBox.ButtonRole.AcceptRole)
        discard_btn = msg.addButton(t('common.discard'), QMessageBox.ButtonRole.DestructiveRole)
        msg.addButton(t('common.cancel'), QMessageBox.ButtonRole.RejectRole)
        msg.setDefaultButton(save_btn)

        msg.exec()
        clicked = msg.clickedButton()

        if clicked == save_btn:
            if self._save_collections():
                event.accept()
            else:
                # Save failed — retry-Dialog (Ja / Nein)
                retry_msg = QMessageBox(self)
                retry_msg.setIcon(QMessageBox.Icon.Warning)
                retry_msg.setWindowTitle(t('ui.menu.file.save_failed_title'))
                retry_msg.setText(t('ui.menu.file.save_failed_msg'))

                yes_btn = retry_msg.addButton(t('common.yes'), QMessageBox.ButtonRole.YesRole)
                retry_msg.addButton(t('common.no'), QMessageBox.ButtonRole.NoRole)
                retry_msg.setDefaultButton(yes_btn)

                retry_msg.exec()
                if retry_msg.clickedButton() == yes_btn:
                    event.accept()
                else:
                    event.ignore()

        elif clicked == discard_btn:
            # Close without saving
            event.accept()
        else:
            # Cancel — stay open
            event.ignore()

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

    def find_missing_metadata(self) -> None:
        """Delegates to ToolsActions (required by MenuBuilder)."""
        self.tools_actions.find_missing_metadata()

    def check_store_availability(self, game: Game) -> None:
        """Delegates to ToolsActions (required by Context Menus)."""
        self.tools_actions.check_store_availability(game)

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
