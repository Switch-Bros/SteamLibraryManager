"""
Main Window - Core UI Logic
Handles the main application window, menus, and game list interactions.
Refactored to use UIHelper and stricter types.
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
    """
    Background thread to load games without freezing the UI.
    """
    progress_update = pyqtSignal(str, int, int)
    finished = pyqtSignal(bool)

    def __init__(self, game_manager: GameManager, user_id: str):
        super().__init__()
        self.game_manager = game_manager
        self.user_id = user_id

    def run(self) -> None:
        def progress_callback(step: str, current: int, total: int):
            self.progress_update.emit(step, current, total)

        success = self.game_manager.load_games(self.user_id, progress_callback)
        self.finished.emit(success)


class MainWindow(QMainWindow):
    """
    The primary application window containing the game list, details view, and menus.
    """

    def __init__(self):
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

        # Threads & Dialogs
        self.load_thread: Optional[GameLoadThread] = None
        self.store_check_thread: Optional[QThread] = None
        self.progress_dialog: Optional[QProgressDialog] = None

        self._create_ui()
        self._load_data()

    def _create_ui(self) -> None:
        """Initialize all UI components, menus, and layouts."""
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

        clear_btn = QPushButton("×")
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
        """Rebuild the toolbar based on state."""
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
        """Fetch the public Persona Name from Steam Community XML."""
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

    # --- OPENID LOGIN LOGIC ---
    def _start_steam_login(self) -> None:
        UIHelper.show_success(self, t('ui.login.info'), t('ui.login.title'))
        self.auth_manager.start_login()
        self.set_status(t('common.loading'))

    def _on_steam_login_success(self, steam_id_64: str) -> None:
        print(t('logs.auth.login_success', id=steam_id_64))
        self.set_status(t('ui.login.status_success'))
        UIHelper.show_success(self, t('ui.login.status_success'), t('ui.login.title'))

        config.STEAM_USER_ID = steam_id_64
        # FIX: Save immediately so login persists after restart!
        config.save()

        # Fetch Name
        self.steam_username = self._fetch_steam_persona_name(steam_id_64)

        # Update User Label
        display_text = self.steam_username if self.steam_username else steam_id_64
        self.user_label.setText(t('ui.main_window.user_label', user_id=display_text))

        # Rebuild Toolbar (to show Name instead of Login button)
        self._refresh_toolbar()

        if self.game_manager:
            self._load_games_with_progress(steam_id_64)

    def _on_steam_login_error(self, error: str) -> None:
        self.set_status(t('ui.login.status_failed'))
        self.reload_btn.show()
        UIHelper.show_error(self, error)

    # --- MAIN LOGIC ---
    def force_save(self) -> None:
        """Manually save the vdf configuration."""
        if self.vdf_parser:
            if self.vdf_parser.save():
                self.set_status(t('common.success'))
            else:
                UIHelper.show_error(self, t('logs.config.save_error', error="Unknown"))

    def show_about(self) -> None:
        QMessageBox.about(self, t('ui.menu.help.about'), t('app.description'))

    def _load_data(self) -> None:
        """Initial Data Load sequence."""
        self.set_status(t('common.loading'))

        if not config.STEAM_PATH:
            UIHelper.show_warning(self, t('logs.main.steam_not_found'))
            self.reload_btn.show()
            return

        short_id, long_id = config.get_detected_user()
        target_id = config.STEAM_USER_ID if config.STEAM_USER_ID else long_id

        if not short_id and not target_id:
            UIHelper.show_warning(self, "No Steam users found.")
            self.reload_btn.show()
            return

        display_id = target_id if target_id else short_id
        self.user_label.setText(t('ui.main_window.user_auto', user_id=display_id))

        config_path = config.get_localconfig_path(short_id)
        if config_path:
            self.vdf_parser = LocalConfigParser(config_path)
            if not self.vdf_parser.load():
                UIHelper.show_error(self, "Error loading localconfig.vdf")
                self.reload_btn.show()
                return

        self.game_manager = GameManager(config.STEAM_API_KEY, config.CACHE_DIR, config.STEAM_PATH)
        self._load_games_with_progress(target_id)

    def _load_games_with_progress(self, user_id: Optional[str]) -> None:
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
        if self.progress_dialog:
            self.progress_dialog.setLabelText(step)
            if total > 0:
                percent = int((current / total) * 100)
                self.progress_dialog.setValue(percent)

    def _on_load_finished(self, success: bool) -> None:
        if self.progress_dialog:
            self.progress_dialog.close()
            self.progress_dialog = None

        if not success or not self.game_manager or not self.game_manager.games:
            UIHelper.show_warning(self, "No games found or error loading.")
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
        """Refreshes the sidebar tree with current game data."""
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
        self.selected_games = games
        if len(games) > 1:
            self.set_status(t('ui.main_window.games_selected', count=len(games)))
        elif len(games) == 1:
            self.set_status(f"{games[0].name}")

    def on_game_selected(self, game: Game) -> None:
        self.selected_game = game
        all_categories = list(self.game_manager.get_all_categories().keys())
        self.details_widget.set_game(game, all_categories)
        if not game.developer:
            if self.game_manager.fetch_game_details(game.app_id):
                self.details_widget.set_game(game, all_categories)

    def _on_category_changed_from_details(self, app_id: str, category: str, checked: bool) -> None:
        game = self.game_manager.get_game(app_id)
        if not game or not self.vdf_parser: return

        if checked:
            if category not in game.categories:
                game.categories.append(category)
                self.vdf_parser.add_app_category(app_id, category)
        else:
            if category in game.categories:
                game.categories.remove(category)
                self.vdf_parser.remove_app_category(app_id, category)

        self.vdf_parser.save()
        self._populate_categories()
        all_categories = list(self.game_manager.get_all_categories().keys())
        self.details_widget.set_game(game, all_categories)

    def on_game_right_click(self, game: Game, pos) -> None:
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

        if len(self.selected_games) > 1:
            menu.addAction(t('ui.menu.edit.auto_categorize'), self.auto_categorize_selected)
            menu.addSeparator()

        menu.addAction(t('ui.context_menu.edit_metadata'), lambda: self.edit_game_metadata(game))
        menu.exec(pos)

    def on_category_right_click(self, category: str, pos) -> None:
        menu = QMenu(self)
        if category in ["Favorites", "Favoriten"]:
            return

        special_cats = ["All Games", "Alle Spiele", "Uncategorized", "Unkategorisiert"]

        if category in special_cats:
            menu.addAction(t('ui.menu.edit.auto_categorize'), lambda: self.auto_categorize_category(category))
        else:
            # Using UIHelper for rename flow would require passing logic, keeping simple calls here for now
            menu.addAction("Rename", lambda: self.rename_category(category))
            menu.addAction("Delete", lambda: self.delete_category(category))
            menu.addSeparator()
            menu.addAction(t('ui.menu.edit.auto_categorize'), lambda: self.auto_categorize_category(category))

        menu.exec(pos)

    def toggle_hide_game(self, game: Game, hide: bool) -> None:
        if not self.vdf_parser: return
        self.vdf_parser.set_app_hidden(game.app_id, hide)

        if self.vdf_parser.save():
            game.hidden = hide

            # Localized status text
            status_word = t('ui.visibility.hidden') if hide else t('ui.visibility.visible')
            self.set_status(f"{status_word}: {game.name}")

            # Localized Popup
            msg = t('ui.visibility.message', game=game.name, status=status_word)
            UIHelper.show_success(self, msg, t('ui.visibility.title'))

    def on_search(self, query: str) -> None:
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
        self.search_entry.clear()
        self._populate_categories()

    def toggle_favorite(self, game: Game) -> None:
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
        import webbrowser
        webbrowser.open(f"https://store.steampowered.com/app/{game.app_id}")

    def check_store_availability(self, game: Game) -> None:
        """Check if game is available on Steam Store."""
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
                        if 'not available' in response.text.lower():
                            self.finished.emit('geo_locked', t('ui.store_check.geo_locked'))
                        else:
                            self.finished.emit('available', t('ui.store_check.available'))
                    elif response.status_code == 302:
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
            else:
                UIHelper.show_warning(self, msg, title)

        self.store_check_thread = StoreCheckThread(game.app_id)
        # noinspection PyUnresolvedReferences
        self.store_check_thread.finished.connect(on_check_finished)
        self.store_check_thread.start()

        def on_check_finished(status: str, details: str):
            progress.close()
            if status == 'available':
                UIHelper.show_success(self, f"{game.name}: {details}", "Store Status")
            else:
                UIHelper.show_warning(self, f"{game.name}: {details}", "Store Status")

        self.store_check_thread = StoreCheckThread(game.app_id)
        # noinspection PyUnresolvedReferences
        self.store_check_thread.finished.connect(on_check_finished)
        self.store_check_thread.start()

    def rename_category(self, old_name: str) -> None:
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
        if not self.vdf_parser: return
        if UIHelper.confirm(
            self,
            t('ui.categories.delete_msg', category=category),
            t('ui.categories.delete_title')
        ):
            self.vdf_parser.delete_category(category)
            self.vdf_parser.save()
            self._populate_categories()

    def auto_categorize(self) -> None:
        if self.selected_games:
            self._show_auto_categorize_dialog(self.selected_games, None)
        else:
            self._show_auto_categorize_dialog(self.game_manager.get_uncategorized_games(), None)

    def auto_categorize_selected(self) -> None:
        if self.selected_games: self._show_auto_categorize_dialog(self.selected_games, None)

    def auto_categorize_category(self, category: str) -> None:
        if category in ["All Games", "Alle Spiele"]:
            self._show_auto_categorize_dialog(self.game_manager.get_all_games(), category)
        elif category in ["Uncategorized", "Unkategorisiert"]:
            self._show_auto_categorize_dialog(self.game_manager.get_uncategorized_games(), category)
        else:
            self._show_auto_categorize_dialog(self.game_manager.get_games_by_category(category), category)

    def _show_auto_categorize_dialog(self, games: List[Game], category_name: Optional[str]) -> None:
        self.dialog_games = games
        if not self.game_manager: return
        dialog = AutoCategorizeDialog(self, games, len(self.game_manager.games), self._do_auto_categorize,
                                      category_name)
        dialog.exec()

    def _do_auto_categorize(self, settings: dict) -> None:
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
                UIHelper.show_success(self, f"Updated {game.name}")

    def bulk_edit_metadata(self) -> None:
        if not self.selected_games:
            UIHelper.show_warning(self, "No games selected.")
            return

        game_names = [g.name for g in self.selected_games]
        dialog = BulkMetadataEditDialog(self, len(self.selected_games), game_names)
        if dialog.exec():
            settings = dialog.get_metadata()
            if settings: self._do_bulk_metadata_edit(self.selected_games, settings)

    def _do_bulk_metadata_edit(self, games: List[Game], settings: Dict) -> None:
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
        UIHelper.show_success(self, f"Updated {len(games)} games.")

    def find_missing_metadata(self) -> None:
        if not self.game_manager: return
        affected = [g for g in self.game_manager.get_all_games() if
                    not g.developer or not g.publisher or not g.release_year]

        if affected:
            dialog = MissingMetadataDialog(self, affected)
            dialog.exec()
        else:
            UIHelper.show_success(self, "All games have metadata!")

    def restore_metadata_changes(self) -> None:
        if not self.appinfo_manager: return
        mod_count = self.appinfo_manager.get_modification_count()
        if mod_count == 0:
            UIHelper.show_success(self, "No changes to restore.")
            return

        dialog = MetadataRestoreDialog(self, mod_count)
        if dialog.exec() and dialog.should_restore():
            try:
                restored = self.appinfo_manager.restore_modifications()
                if restored > 0:
                    UIHelper.show_success(self, f"Restored {restored} games.")
                    self.refresh_data()
            except Exception as e:
                UIHelper.show_error(self, str(e))

    def refresh_data(self) -> None:
        self._load_data()

    def show_settings(self) -> None:
        dialog = SettingsDialog(self)
        # noinspection PyUnresolvedReferences
        dialog.language_changed.connect(self._on_ui_language_changed_live)
        if dialog.exec():
            settings = dialog.get_settings()
            if settings: self._apply_settings(settings)

    def _on_ui_language_changed_live(self, new_language: str) -> None:
        config.UI_LANGUAGE = new_language
        init_i18n(new_language)
        self._refresh_menubar()
        self._refresh_toolbar()
        self.setWindowTitle(t('ui.main_window.title'))
        self.set_status(t('ui.main_window.status_ready'))

    def _refresh_menubar(self) -> None:
        """Rebuilds menu and toolbar on language switch."""
        # 1. Clear Menu Bar
        self.menuBar().clear()

        # 2. Remove Toolbar explicitly to prevent duplicates!
        if hasattr(self, 'toolbar') and self.toolbar:
            self.removeToolBar(self.toolbar)
            self.toolbar.deleteLater()  # Clean up memory
            self.toolbar = None

        # 3. Re-create UI
        self._create_ui()

    def _apply_settings(self, settings: dict) -> None:
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
        UIHelper.show_success(self, "Settings saved.")

    @staticmethod
    def _save_settings(settings: dict) -> None:
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
        self.statusbar.showMessage(text)