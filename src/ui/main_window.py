"""
Main application window for Steam Library Manager.

This module contains the primary application window that displays the game
library, handles user interactions, and coordinates between various managers
and dialogs. It provides the main interface for browsing, searching, and
managing Steam games.
"""
from pathlib import Path
from typing import Optional, List, Dict

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLineEdit, QPushButton, QLabel, QToolBar, QMenu,
    QMessageBox, QSplitter, QProgressDialog, QApplication
)
from PyQt6.QtCore import Qt, QUrl, QThread, pyqtSignal
from PyQt6.QtGui import QAction, QDesktopServices, QIcon

import requests
# noinspection PyPep8Naming
import xml.etree.ElementTree as ET

from src.config import config
from src.core.game_manager import GameManager, Game
from src.core.localconfig_parser import LocalConfigParser
from src.core.appinfo_manager import AppInfoManager
from src.core.steam_auth import SteamAuthManager
from src.integrations.steam_store import SteamStoreScraper

# Dialogs
from src.ui.auto_categorize_dialog import AutoCategorizeDialog
from src.ui.metadata_dialogs import (
    MetadataEditDialog,
    BulkMetadataEditDialog,
    MetadataRestoreDialog
)
from src.ui.missing_metadata_dialog import MissingMetadataDialog
from src.ui.settings_dialog import SettingsDialog

# Components
from src.ui.game_details_widget import GameDetailsWidget
from src.ui.components.category_tree import GameTreeWidget
from src.ui.components.ui_helper import UIHelper

from src.utils.i18n import t, init_i18n


class GameLoadThread(QThread):
    """Background thread for loading games without blocking the UI.

    Loads game data from Steam API and local files in a separate thread,
    emitting progress updates that can be displayed in a progress dialog.

    Attributes:
        game_manager: The GameManager instance to use for loading.
        user_id: The Steam user ID to load games for.

    Signals:
        progress_update: Emitted during loading with (step_name, current, total).
        finished: Emitted when loading completes with success status.
    """

    progress_update = pyqtSignal(str, int, int)
    finished = pyqtSignal(bool)

    def __init__(self, game_manager: GameManager, user_id: str):
        """Initializes the game load thread.

        Args:
            game_manager: The GameManager instance to use for loading.
            user_id: The Steam user ID to load games for.
        """
        super().__init__()
        self.game_manager = game_manager
        self.user_id = user_id

    def run(self) -> None:
        """Executes the game loading process.

        Calls the game manager's load_games method with a progress callback
        and emits the finished signal with the result.
        """

        def progress_callback(step: str, current: int, total: int):
            self.progress_update.emit(step, current, total)

        success = self.game_manager.load_games(self.user_id, progress_callback)
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
        self.steam_scraper: Optional[SteamStoreScraper] = None
        self.appinfo_manager: Optional[AppInfoManager] = None

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
        self.load_thread: Optional[GameLoadThread] = None
        self.store_check_thread: Optional[QThread] = None
        self.progress_dialog: Optional[QProgressDialog] = None

        self._create_ui()
        self._load_data()

    def _create_ui(self) -> None:
        """Initializes all UI components, menus, and layouts.

        Creates the menu bar, toolbar, central widget with splitter layout,
        game tree sidebar, details panel, search bar, and status bar.
        """
        menubar = self.menuBar()

        # 1. FILE MENU
        file_menu = menubar.addMenu(t('ui.menu.file.root'))

        refresh_action = QAction(t('ui.menu.file.refresh'), self)
        # noinspection PyUnresolvedReferences
        refresh_action.triggered.connect(self.refresh_data)
        file_menu.addAction(refresh_action)

        save_action = QAction(t('ui.menu.file.save'), self)
        # noinspection PyUnresolvedReferences
        save_action.triggered.connect(self.force_save)
        file_menu.addAction(save_action)

        file_menu.addSeparator()

        exit_action = QAction(t('ui.menu.file.exit'), self)
        # noinspection PyUnresolvedReferences
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # 2. EDIT MENU
        edit_menu = menubar.addMenu(t('ui.menu.edit.root'))

        bulk_edit_action = QAction(t('ui.menu.edit.bulk_edit'), self)
        # noinspection PyUnresolvedReferences
        bulk_edit_action.triggered.connect(self.bulk_edit_metadata)
        edit_menu.addAction(bulk_edit_action)

        auto_cat_action = QAction(t('ui.menu.edit.auto_categorize'), self)
        # noinspection PyUnresolvedReferences
        auto_cat_action.triggered.connect(self.auto_categorize)
        edit_menu.addAction(auto_cat_action)

        # 3. SETTINGS MENU (Moved settings logic here)
        settings_menu = menubar.addMenu(t('ui.settings.title'))

        settings_action = QAction(t('ui.settings.title'), self)
        # noinspection PyUnresolvedReferences
        settings_action.triggered.connect(self.show_settings)
        settings_menu.addAction(settings_action)

        settings_menu.addSeparator()

        # Restore Metadata (Using Import JSON key as closest match/placeholder)
        restore_action = QAction(t('ui.menu.file.import_json'), self)
        # noinspection PyUnresolvedReferences
        restore_action.triggered.connect(self.restore_metadata_changes)
        settings_menu.addAction(restore_action)

        # 4. TOOLS MENU
        tools_menu = menubar.addMenu(t('ui.menu.tools.root'))

        find_missing_action = QAction(t('ui.menu.tools.missing_meta'), self)
        # noinspection PyUnresolvedReferences
        find_missing_action.triggered.connect(self.find_missing_metadata)
        tools_menu.addAction(find_missing_action)

        # 5. HELP MENU
        help_menu = menubar.addMenu(t('ui.menu.help.root'))

        github_action = QAction(t('ui.menu.help.github'), self)
        # noinspection PyUnresolvedReferences
        github_action.triggered.connect(
            lambda: QDesktopServices.openUrl(QUrl("https://github.com/Switch-Bros/SteamLibraryManager")))
        help_menu.addAction(github_action)

        donate_action = QAction(t('ui.menu.help.donate'), self)
        # noinspection PyUnresolvedReferences
        donate_action.triggered.connect(lambda: QDesktopServices.openUrl(QUrl("https://paypal.me/")))
        help_menu.addAction(donate_action)

        help_menu.addSeparator()

        about_action = QAction(t('ui.menu.help.about'), self)
        # noinspection PyUnresolvedReferences
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)

        # User Info Label
        self.user_label = QLabel(t('common.unknown'))
        self.user_label.setStyleSheet("padding: 5px 10px;")
        menubar.setCornerWidget(self.user_label, Qt.Corner.TopRightCorner)

        # Toolbar
        self.toolbar = QToolBar()
        self.addToolBar(self.toolbar)
        self._refresh_toolbar()

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
        # noinspection PyUnresolvedReferences
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
        splitter.addWidget(self.details_widget)

        splitter.setSizes([350, 1050])
        layout.addWidget(splitter)

        # Statusbar
        self.statusbar = self.statusBar()
        self.reload_btn = QPushButton(t('ui.menu.file.refresh'))
        # noinspection PyUnresolvedReferences
        self.reload_btn.clicked.connect(self.refresh_data)
        self.reload_btn.setMaximumWidth(150)
        self.reload_btn.hide()
        self.statusbar.addPermanentWidget(self.reload_btn)

        self.set_status(t('ui.main_window.status_ready'))

    def _refresh_toolbar(self) -> None:
        """Rebuilds the toolbar based on current authentication state.

        Clears and recreates toolbar actions. Shows either a login button
        or the logged-in username depending on authentication state.
        """
        self.toolbar.clear()

        self.toolbar.addAction(t('ui.menu.file.refresh'), self.refresh_data)
        self.toolbar.addAction(t('ui.menu.edit.auto_categorize'), self.auto_categorize)
        self.toolbar.addSeparator()
        self.toolbar.addAction(t('ui.settings.title'), self.show_settings)
        self.toolbar.addSeparator()

        if self.steam_username:
            user_action = QAction(self.steam_username, self)

            # Localized Tooltip
            tooltip = t('ui.login.logged_in_as', user=self.steam_username)
            user_action.setToolTip(tooltip)

            user_action.triggered.connect(
                lambda: UIHelper.show_success(self, tooltip, "Steam")
            )

            icon_path = config.ICONS_DIR / 'steam_login.png'
            if icon_path.exists():
                user_action.setIcon(QIcon(str(icon_path)))

            self.toolbar.addAction(user_action)
        else:
            login_action = QAction(t('ui.login.button'), self)
            icon_path = config.ICONS_DIR / 'steam_login.png'
            if icon_path.exists():
                login_action.setIcon(QIcon(str(icon_path)))

            # noinspection PyUnresolvedReferences
            login_action.triggered.connect(self._start_steam_login)
            self.toolbar.addAction(login_action)

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

        Shows an info dialog and starts the authentication manager.
        """
        UIHelper.show_success(self, t('ui.login.info'), t('ui.login.title'))
        self.auth_manager.start_login()
        self.set_status(t('common.loading'))

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
            if self.vdf_parser.save():
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

        config_path = config.get_localconfig_path(short_id)
        if config_path:
            self.vdf_parser = LocalConfigParser(config_path)
            if not self.vdf_parser.load():
                UIHelper.show_error(self, t('ui.errors.localconfig_load_error'))
                self.reload_btn.show()
                return

        self.game_manager = GameManager(config.STEAM_API_KEY, config.CACHE_DIR, config.STEAM_PATH)
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

        self.load_thread = GameLoadThread(self.game_manager, user_id or "local")
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

        if not success or not self.game_manager or not self.game_manager.games:
            UIHelper.show_warning(self, t('ui.errors.no_games_found'))
            self.reload_btn.show()
            self.set_status(t('common.error'))
            return

        if self.vdf_parser:
            self.game_manager.merge_with_localconfig(self.vdf_parser)

        self.steam_scraper = SteamStoreScraper(config.CACHE_DIR, config.TAGS_LANGUAGE)
        self.appinfo_manager = AppInfoManager(config.STEAM_PATH)
        self.appinfo_manager.load_appinfo()
        self.game_manager.apply_metadata_overrides(self.appinfo_manager)
        self._populate_categories()

        status_msg = self.game_manager.get_load_source_message()
        self.set_status(status_msg)
        self.reload_btn.hide()

    def _populate_categories(self) -> None:
        """Refreshes the sidebar tree with current game data.

        Builds category data including All Games, Favorites, Uncategorized,
        and user-defined categories, then updates the tree widget.
        """
        if not self.game_manager: return
        categories_data = {}
        all_games = sorted(self.game_manager.get_all_games(), key=lambda g: g.sort_name.lower())

        # Localized Category Names
        categories_data[t('ui.categories.all_games')] = all_games

        favorites = sorted(self.game_manager.get_favorites(), key=lambda g: g.sort_name.lower())
        if favorites:
            categories_data[t('ui.categories.favorites')] = favorites

        uncat = sorted(self.game_manager.get_uncategorized_games(), key=lambda g: g.sort_name.lower())
        if uncat:
            categories_data[t('ui.categories.uncategorized')] = uncat

        cats = self.game_manager.get_all_categories()
        for cat_name in sorted(cats.keys()):
            if cat_name != 'favorite':
                cat_games = sorted(self.game_manager.get_games_by_category(cat_name), key=lambda g: g.sort_name.lower())
                categories_data[cat_name] = cat_games

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
        self.details_widget.set_game(game, all_categories)
        # Fetch details if missing developer, proton rating, or steam deck status
        if not game.developer or not game.proton_db_rating or not game.steam_deck_status:
            if self.game_manager.fetch_game_details(game.app_id):
                self.details_widget.set_game(game, all_categories)

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
                app_id = game_item.data(0, Qt.ItemDataRole.UserRole)
                if app_id and app_id in app_ids:
                    game_item.setSelected(True)

        # Re-enable signals
        self.tree.blockSignals(False)

        # Manually update selected_games list
        self.selected_games = [self.game_manager.get_game(app_id) for app_id in app_ids]
        self.selected_games = [g for g in self.selected_games if g is not None]

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

        # Apply category change to all games
        for game in games_to_update:
            if checked:
                if category not in game.categories:
                    game.categories.append(category)
                    self.vdf_parser.add_app_category(game.app_id, category)
            else:
                if category in game.categories:
                    game.categories.remove(category)
                    self.vdf_parser.remove_app_category(game.app_id, category)

        self.vdf_parser.save()

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
                self.vdf_parser.add_app_category(game.app_id, target_category)

        # Save changes to VDF file
        self.vdf_parser.save()

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
            menu.exec(pos)
            return

        # Single category
        if category == t('ui.categories.favorites'):
            return

        special_cats = [t('ui.categories.all_games'), t('ui.categories.uncategorized')]

        if category in special_cats:
            menu.addAction(t('ui.menu.edit.auto_categorize'), lambda: self.auto_categorize_category(category))
        else:
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

        if self.vdf_parser.save():
            game.hidden = hide

            status_word = t('ui.visibility.hidden') if hide else t('ui.visibility.visible')
            self.set_status(f"{status_word}: {game.name}")

            msg = t('ui.visibility.message', game=game.name, status=status_word)
            UIHelper.show_success(self, msg, t('ui.visibility.title'))

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
        results = [g for g in self.game_manager.get_all_games() if query.lower() in g.name.lower()]

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
            self.vdf_parser.remove_app_category(game.app_id, 'favorite')
        else:
            if 'favorite' not in game.categories: game.categories.append('favorite')
            self.vdf_parser.add_app_category(game.app_id, 'favorite')

        self.vdf_parser.save()
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
                    # Use Steam Store API for reliable geo-blocking detection
                    # First check with user's country (DE for Germany)
                    api_url_de = f"https://store.steampowered.com/api/appdetails?appids={self.app_id}&cc=DE"
                    response_de = requests.get(api_url_de, timeout=10)

                    if response_de.status_code != 200:
                        self.finished.emit('unknown', t('ui.store_check.unknown', code=response_de.status_code))
                        return

                    data_de = response_de.json()

                    if self.app_id in data_de:
                        app_data_de = data_de[self.app_id]

                        if app_data_de.get('success'):
                            # Available in Germany
                            self.finished.emit('available', t('ui.store_check.available'))
                        else:
                            # Not available in Germany - check if it's geo-blocked or delisted
                            # Try with US country code
                            api_url_us = f"https://store.steampowered.com/api/appdetails?appids={self.app_id}&cc=US"
                            response_us = requests.get(api_url_us, timeout=10)

                            if response_us.status_code == 200:
                                data_us = response_us.json()

                                if self.app_id in data_us:
                                    app_data_us = data_us[self.app_id]

                                    if app_data_us.get('success'):
                                        # Available in US but not in DE → Geo-blocked
                                        self.finished.emit('geo_locked', t('ui.store_check.geo_locked'))
                                    else:
                                        # Not available anywhere → Delisted
                                        self.finished.emit('delisted', t('ui.store_check.delisted'))
                                else:
                                    self.finished.emit('delisted', t('ui.store_check.delisted'))
                            else:
                                # Can't check US, assume delisted
                                self.finished.emit('delisted', t('ui.store_check.delisted'))
                    else:
                        self.finished.emit('unknown', t('ui.store_check.unknown', code=0))

                except Exception as ex:
                    self.finished.emit('unknown', str(ex))

        def on_check_finished(status: str, details: str):
            progress.close()
            title = t('ui.store_check.title')
            msg = f"{game.name}: {details}"

            if status == 'available':
                UIHelper.show_success(self, msg, title)
            else:
                UIHelper.show_warning(self, msg, title)

        self.store_check_thread = StoreCheckThread(game.app_id)
        # noinspection PyUnresolvedReferences
        self.store_check_thread.finished.connect(on_check_finished)
        self.store_check_thread.start()

    def rename_category(self, old_name: str) -> None:
        """Prompts the user to rename a category.

        Args:
            old_name: The current name of the category to rename.
        """
        if not self.vdf_parser: return
        new_name, ok = UIHelper.ask_text(
            self,
            t('ui.categories.rename_title'),
            t('ui.categories.rename_msg', old=old_name)
        )
        if ok and new_name and new_name != old_name:
            self.vdf_parser.rename_category(old_name, new_name)
            self.vdf_parser.save()
            self._populate_categories()

    def delete_category(self, category: str) -> None:
        """Prompts the user to delete a category.

        Args:
            category: The name of the category to delete.
        """
        if not self.vdf_parser: return
        if UIHelper.confirm(
                self,
                t('ui.categories.delete_msg', category=category),
                t('ui.categories.delete_title')
        ):
            self.vdf_parser.delete_category(category)
            self.vdf_parser.save()
            self._populate_categories()

    def merge_categories(self, categories: List[str]) -> None:
        """
        Merges multiple categories into one.

        Shows a dialog to select the target category, then moves all games
        from the other categories into the target and deletes the source categories.

        Args:
            categories: List of category names to merge.
        """
        if not self.vdf_parser or len(categories) < 2:
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

            # Merge: Move all games from source categories to target
            for source_cat in source_categories:
                games_in_source = self.game_manager.get_games_by_category(source_cat)
                for game in games_in_source:
                    # Add to target if not already there
                    if target_category not in game.categories:
                        game.categories.append(target_category)
                        self.vdf_parser.add_app_category(game.app_id, target_category)
                    # Remove from source
                    if source_cat in game.categories:
                        game.categories.remove(source_cat)
                        self.vdf_parser.remove_app_category(game.app_id, source_cat)

                # Delete the source category
                self.vdf_parser.delete_category(source_cat)

            self.vdf_parser.save()
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
            self._show_auto_categorize_dialog(self.game_manager.get_all_games(), category)
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
        if not self.game_manager: return
        dialog = AutoCategorizeDialog(self, games, len(self.game_manager.games), self._do_auto_categorize,
                                      category_name)
        dialog.exec()

    def _do_auto_categorize(self, settings: dict) -> None:
        """Executes the auto-categorization process with the given settings.

        Args:
            settings: Dictionary containing scope, methods, and tags_count options.
        """
        if not settings or not self.vdf_parser: return

        games = self.game_manager.get_all_games() if settings['scope'] == 'all' else self.dialog_games
        methods = settings['methods']

        progress = QProgressDialog(
            t('ui.auto_categorize.processing', current=0, total=len(games)),
            t('common.cancel'), 0, len(methods) * len(games), self
        )
        progress.setWindowModality(Qt.WindowModality.WindowModal)

        step = 0
        for method in methods:
            if method == 'tags' and self.steam_scraper:
                for i, game in enumerate(games):
                    if progress.wasCanceled(): break
                    progress.setValue(step + i)
                    if i % 10 == 0:
                        progress.setLabelText(t('ui.auto_categorize.status_tags', game=game.name[:30]))
                    QApplication.processEvents()

                    all_tags = self.steam_scraper.fetch_tags(game.app_id)
                    tags = all_tags[:settings['tags_count']]

                    for tag in tags:
                        self.vdf_parser.add_app_category(game.app_id, tag)
                        if tag not in game.categories: game.categories.append(tag)
                step += len(games)

            elif method == 'publisher':
                for i, game in enumerate(games):
                    if progress.wasCanceled(): break
                    progress.setValue(step + i)
                    if game.publisher:
                        cat = t('ui.auto_categorize.cat_publisher', name=game.publisher)
                        self.vdf_parser.add_app_category(game.app_id, cat)
                        if cat not in game.categories: game.categories.append(cat)
                step += len(games)

            elif method == 'franchise':
                for i, game in enumerate(games):
                    if progress.wasCanceled(): break
                    progress.setValue(step + i)
                    franchise = SteamStoreScraper.detect_franchise(game.name)
                    if franchise:
                        cat = t('ui.auto_categorize.cat_franchise', name=franchise)
                        self.vdf_parser.add_app_category(game.app_id, cat)
                        if cat not in game.categories: game.categories.append(cat)
                step += len(games)

            elif method == 'genre':
                for i, game in enumerate(games):
                    if progress.wasCanceled(): break
                    progress.setValue(step + i)
                    if game.genres:
                        for genre in game.genres:
                            self.vdf_parser.add_app_category(game.app_id, genre)
                            if genre not in game.categories: game.categories.append(genre)
                step += len(games)

        self.vdf_parser.save()
        progress.close()
        self._populate_categories()
        UIHelper.show_success(self, t('common.success'))

    def edit_game_metadata(self, game: Game) -> None:
        """Opens the metadata edit dialog for a single game.

        Args:
            game: The game to edit metadata for.
        """
        if not self.appinfo_manager: return
        meta = self.appinfo_manager.get_app_metadata(game.app_id)

        # Fill defaults
        for key, val in {'name': game.name, 'developer': game.developer, 'publisher': game.publisher,
                         'release_date': game.release_year}.items():
            if not meta.get(key): meta[key] = val

        original_meta = self.appinfo_manager.modifications.get(game.app_id, {}).get('original', meta.copy())
        dialog = MetadataEditDialog(self, game.name, meta, original_meta)

        if dialog.exec():
            new_meta = dialog.get_metadata()
            if new_meta:
                write_vdf = new_meta.pop('write_to_vdf', False)
                self.appinfo_manager.set_app_metadata(game.app_id, new_meta)
                self.appinfo_manager.save_appinfo()

                if write_vdf:
                    self.appinfo_manager.load_appinfo()
                    self.appinfo_manager.write_to_vdf(backup=True)

                if new_meta.get('name'): game.name = new_meta['name']
                self._populate_categories()
                self.on_game_selected(game)
                UIHelper.show_success(self, t('ui.metadata_editor.updated_single', game=game.name))

    def bulk_edit_metadata(self) -> None:
        """Opens the bulk metadata edit dialog for selected games."""
        if not self.selected_games:
            UIHelper.show_warning(self, t('ui.errors.no_selection'))
            return

        game_names = [g.name for g in self.selected_games]
        dialog = BulkMetadataEditDialog(self, len(self.selected_games), game_names)
        if dialog.exec():
            settings = dialog.get_metadata()
            if settings: self._do_bulk_metadata_edit(self.selected_games, settings)

    def _do_bulk_metadata_edit(self, games: List[Game], settings: Dict) -> None:
        """Applies bulk metadata changes to the specified games.

        Args:
            games: List of games to apply changes to.
            settings: Dictionary containing the metadata changes and name modifications.
        """
        if not self.appinfo_manager: return
        name_mods = settings.pop('name_modifications', {})
        for game in games:
            new_name = game.name
            if name_mods.get('prefix'): new_name = name_mods['prefix'] + new_name
            if name_mods.get('suffix'): new_name = new_name + name_mods['suffix']
            if name_mods.get('remove'): new_name = new_name.replace(name_mods['remove'], '')

            meta = settings.copy()
            if new_name != game.name: meta['name'] = new_name
            self.appinfo_manager.set_app_metadata(game.app_id, meta)

        self.appinfo_manager.save_appinfo()
        self._populate_categories()
        UIHelper.show_success(self, t('ui.metadata_editor.updated_bulk', count=len(games)))

    def find_missing_metadata(self) -> None:
        """Shows a dialog listing games with incomplete metadata."""
        if not self.game_manager: return
        affected = [g for g in self.game_manager.get_all_games() if
                    not g.developer or not g.publisher or not g.release_year]

        if affected:
            dialog = MissingMetadataDialog(self, affected)
            dialog.exec()
        else:
            UIHelper.show_success(self, t('ui.tools.missing_metadata.all_complete'))

    def restore_metadata_changes(self) -> None:
        """Opens the metadata restore dialog to revert modifications."""
        if not self.appinfo_manager: return
        mod_count = self.appinfo_manager.get_modification_count()
        if mod_count == 0:
            UIHelper.show_success(self, t('ui.metadata_editor.no_changes_to_restore'))
            return

        dialog = MetadataRestoreDialog(self, mod_count)
        if dialog.exec() and dialog.should_restore():
            try:
                restored = self.appinfo_manager.restore_modifications()
                if restored > 0:
                    UIHelper.show_success(self, t('ui.metadata_editor.restored_count', count=restored))
                    self.refresh_data()
            except Exception as e:
                UIHelper.show_error(self, str(e))

    def refresh_data(self) -> None:
        """Reloads all game data from scratch."""
        self._load_data()

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
        """Rebuilds menu bar and toolbar after language change.

        Clears the menu bar, removes the toolbar to prevent duplicates,
        and recreates the entire UI with new translations.
        """
        self.menuBar().clear()

        if hasattr(self, 'toolbar') and self.toolbar:
            self.removeToolBar(self.toolbar)
            self.toolbar.deleteLater()
            self.toolbar = None

        self._create_ui()

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
            text: The status message to display.
        """
        self.statusbar.showMessage(text)