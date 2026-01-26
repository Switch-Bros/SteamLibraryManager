"""
Main Window - With Progress Dialog & Reload Button
Speichern als: src/ui/main_window.py
"""
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLineEdit, QPushButton, QLabel, QToolBar, QMenu,
    QMessageBox, QInputDialog, QSplitter,
    QProgressDialog, QApplication
)
from PyQt6.QtCore import Qt, QUrl, QThread, pyqtSignal
from PyQt6.QtGui import QAction, QDesktopServices, QIcon
from typing import Optional, List, Dict
from pathlib import Path

import requests
# noinspection PyPep8Naming
import xml.etree.ElementTree as ET

from src.config import config
from src.core.game_manager import GameManager, Game
from src.core.localconfig_parser import LocalConfigParser
from src.core.appinfo_manager import AppInfoManager
from src.core.steam_auth import SteamAuthManager
from src.integrations.steam_store import SteamStoreScraper
from src.ui.auto_categorize_dialog import AutoCategorizeDialog
from src.ui.metadata_dialogs import (
    MetadataEditDialog,
    BulkMetadataEditDialog,
    MetadataRestoreDialog
)
from src.ui.missing_metadata_dialog import MissingMetadataDialog
from src.utils.i18n import t, init_i18n
from src.ui.settings_dialog import SettingsDialog
from src.ui.game_details_widget import GameDetailsWidget
from src.ui.components.category_tree import GameTreeWidget


class GameLoadThread(QThread):
    """Thread für das Laden von Spielen mit Progress-Updates"""
    progress_update = pyqtSignal(str, int, int)
    finished = pyqtSignal(bool)

    def __init__(self, game_manager: GameManager, user_id: str):
        super().__init__()
        self.game_manager = game_manager
        self.user_id = user_id

    def run(self):
        def progress_callback(step: str, current: int, total: int):
            self.progress_update.emit(step, current, total)

        success = self.game_manager.load_games(self.user_id, progress_callback)
        self.finished.emit(success)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(t('ui.main.title'))
        self.resize(1400, 800)

        # Managers
        self.game_manager: Optional[GameManager] = None
        self.vdf_parser: Optional[LocalConfigParser] = None
        self.steam_scraper: Optional[SteamStoreScraper] = None
        self.appinfo_manager: Optional[AppInfoManager] = None

        # Auth Manager
        self.auth_manager = SteamAuthManager()
        # noinspection PyUnresolvedReferences
        self.auth_manager.auth_success.connect(self._on_steam_login_success)
        # noinspection PyUnresolvedReferences
        self.auth_manager.auth_error.connect(self._on_steam_login_error)

        self.selected_game: Optional[Game] = None
        self.selected_games: List[Game] = []
        self.dialog_games: List[Game] = []

        # Steam Username (für Toolbar)
        self.steam_username: Optional[str] = None

        # Loading Thread
        self.load_thread: Optional[GameLoadThread] = None
        self.progress_dialog: Optional[QProgressDialog] = None

        self._create_ui()
        self._load_data()

    def _create_ui(self):
        menubar = self.menuBar()

        # 1. FILE
        file_menu = menubar.addMenu(t('ui.menu.file'))

        refresh_action = QAction(t('ui.menu.refresh'), self)
        # noinspection PyUnresolvedReferences
        refresh_action.triggered.connect(self.refresh_data)
        file_menu.addAction(refresh_action)

        save_action = QAction(t('ui.menu.save'), self)
        # noinspection PyUnresolvedReferences
        save_action.triggered.connect(self.force_save)
        file_menu.addAction(save_action)

        file_menu.addSeparator()

        exit_action = QAction(t('ui.menu.exit'), self)
        # noinspection PyUnresolvedReferences
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # 2. EDIT
        edit_menu = menubar.addMenu(t('ui.menu.edit'))

        bulk_edit_action = QAction(t('ui.menu.bulk_edit'), self)
        # noinspection PyUnresolvedReferences
        bulk_edit_action.triggered.connect(self.bulk_edit_metadata)
        edit_menu.addAction(bulk_edit_action)

        auto_cat_action = QAction(t('ui.toolbar.auto_categorize'), self)
        # noinspection PyUnresolvedReferences
        auto_cat_action.triggered.connect(self.auto_categorize)
        edit_menu.addAction(auto_cat_action)

        # 3. SETTINGS
        settings_menu = menubar.addMenu(t('ui.toolbar.settings'))

        settings_action = QAction(t('ui.menu.settings'), self)
        # noinspection PyUnresolvedReferences
        settings_action.triggered.connect(self.show_settings)
        settings_menu.addAction(settings_action)

        settings_menu.addSeparator()

        restore_action = QAction(t('ui.menu.restore'), self)
        # noinspection PyUnresolvedReferences
        restore_action.triggered.connect(self.restore_metadata_changes)
        settings_menu.addAction(restore_action)

        # 4. TOOLS
        tools_menu = menubar.addMenu(t('ui.menu.tools'))

        find_missing_action = QAction(t('ui.menu.find_missing_metadata'), self)
        # noinspection PyUnresolvedReferences
        find_missing_action.triggered.connect(self.find_missing_metadata)
        tools_menu.addAction(find_missing_action)

        # 5. HELP
        help_menu = menubar.addMenu(t('ui.menu.help'))

        github_action = QAction(t('ui.menu.github'), self)
        # noinspection PyUnresolvedReferences
        github_action.triggered.connect(lambda: QDesktopServices.openUrl(QUrl("https://github.com/")))
        help_menu.addAction(github_action)

        donate_action = QAction(t('ui.menu.donate'), self)
        # noinspection PyUnresolvedReferences
        donate_action.triggered.connect(lambda: QDesktopServices.openUrl(QUrl("https://paypal.me/DeinAccount")))
        help_menu.addAction(donate_action)

        help_menu.addSeparator()

        about_action = QAction(t('ui.menu.about'), self)
        # noinspection PyUnresolvedReferences
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)

        # User Info Label
        self.user_label = QLabel(t('ui.status.not_logged_in'))
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
        search_layout.addWidget(QLabel(t('ui.main.search_icon')))
        self.search_entry = QLineEdit()
        self.search_entry.setPlaceholderText(t('ui.main.search_placeholder'))
        # noinspection PyUnresolvedReferences
        self.search_entry.textChanged.connect(self.on_search)
        search_layout.addWidget(self.search_entry)
        clear_btn = QPushButton(t('ui.main.clear_search'))
        # noinspection PyUnresolvedReferences
        clear_btn.clicked.connect(self.clear_search)
        clear_btn.setMaximumWidth(30)
        search_layout.addWidget(clear_btn)
        left_layout.addLayout(search_layout)

        # Tree Controls
        btn_layout = QHBoxLayout()
        expand_btn = QPushButton(t('ui.categories.sym_expand') + " " + t('ui.main.expand_all'))
        # noinspection PyUnresolvedReferences
        expand_btn.clicked.connect(lambda: self.tree.expandAll())
        btn_layout.addWidget(expand_btn)

        collapse_btn = QPushButton(t('ui.categories.sym_collapse') + " " + t('ui.main.collapse_all'))
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

        # Statusbar mit Reload-Button
        self.statusbar = self.statusBar()

        # Reload Button (initial versteckt)
        self.reload_btn = QPushButton(t('ui.status.reload_button'))
        # noinspection PyUnresolvedReferences
        self.reload_btn.clicked.connect(self.refresh_data)
        self.reload_btn.setMaximumWidth(100)
        self.reload_btn.hide()
        self.statusbar.addPermanentWidget(self.reload_btn)

        self.set_status(t('ui.status.ready'))

    def _refresh_toolbar(self):
        self.toolbar.clear()
        # Verwende die t()-Keys, die du bereits in den JSONs hast
        self.toolbar.addAction(t('ui.toolbar.refresh'), self.refresh_data)
        self.toolbar.addAction(t('ui.toolbar.auto_categorize'), self.auto_categorize)
        self.toolbar.addSeparator()
        self.toolbar.addAction(t('ui.toolbar.settings'), self.show_settings)
        self.toolbar.addSeparator()

        # LOGIN BUTTON LOGIK
        if self.steam_username:
            # Wenn eingeloggt: Zeige Profilnamen (mit Sonderzeichen)
            user_action = QAction(self.steam_username, self)

            # FIX: Tooltip lokalisiert
            user_action.setToolTip(t('ui.toolbar.logged_in_as', user=self.steam_username))

            # FIX: Info-Box lokalisiert
            user_action.triggered.connect(
                lambda: QMessageBox.information(self, "Steam", t('ui.toolbar.logged_in_as', user=self.steam_username))
            )

            icon_path = config.ICONS_DIR / 'steam_login.png'
            if icon_path.exists():
                user_action.setIcon(QIcon(str(icon_path)))

            self.toolbar.addAction(user_action)
        else:
            # Wenn NICHT eingeloggt: Zeige Login Button
            login_action = QAction(t('ui.toolbar.login'), self)
            icon_path = config.ICONS_DIR / 'steam_login.png'
            if icon_path.exists():
                login_action.setIcon(QIcon(str(icon_path)))

            # noinspection PyUnresolvedReferences
            login_action.triggered.connect(self._start_steam_login)
            self.toolbar.addAction(login_action)

    @staticmethod
    def _fetch_steam_persona_name(steam_id: str) -> str:
        """Holt den Anzeigenamen (Persona Name) von Steam"""
        try:
            # XML Profil-Schnittstelle (öffentlich)
            url = f"https://steamcommunity.com/profiles/{steam_id}/?xml=1"
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                tree = ET.fromstring(response.content)
                steam_id_element = tree.find('steamID')
                if steam_id_element is not None:
                    return steam_id_element.text
        except Exception as e:
            # FIX: Nutzt jetzt t() für das Log
            print(t('logs.auth.profile_error', error=str(e)))

        # Fallback auf ID
        return steam_id

    # --- OPENID LOGIN LOGIC ---
    def _start_steam_login(self):
        QMessageBox.information(self, t('ui.login.title'), t('ui.login.info'))
        self.auth_manager.start_login()
        self.set_status(t('ui.login.status_waiting'))

    def _on_steam_login_success(self, steam_id_64: str):
        print(t('logs.auth.login_success', id=steam_id_64))
        self.set_status(t('ui.login.status_success'))
        QMessageBox.information(self, t('ui.login.title'), t('ui.login.status_success'))

        config.STEAM_USER_ID = steam_id_64

        # NEU: Namen holen und speichern
        self.steam_username = self._fetch_steam_persona_name(steam_id_64)

        # Update User Label
        display_text = self.steam_username if self.steam_username else steam_id_64
        self.user_label.setText(t('ui.main.user_label', user_id=display_text))

        # NEU: Toolbar neu bauen (Button zeigt jetzt Name)
        self._refresh_toolbar()

        if self.game_manager:
            self._load_games_with_progress(steam_id_64)

    def _on_steam_login_error(self, error: str):
        self.set_status(t('ui.login.status_failed'))
        self.reload_btn.show()
        QMessageBox.critical(self, t('ui.dialogs.error'), error)

    # --- MAIN LOGIC ---
    def force_save(self):
        if self.vdf_parser:
            if self.vdf_parser.save():
                self.set_status(t('ui.status.saved_backup'))
            else:
                QMessageBox.critical(self, t('ui.dialogs.error'), t('ui.errors.save_failed'))

    def show_about(self):
        QMessageBox.about(self, t('ui.menu.about'), t('ui.dialogs.about_text'))

    def _load_data(self):
        """Initial Load beim Start"""
        self.set_status(t('ui.status.loading'))

        if not config.STEAM_PATH:
            QMessageBox.warning(self, t('ui.dialogs.error'), t('errors.steam_not_found'))
            self.reload_btn.show()
            return

        short_id, long_id = config.get_detected_user()
        target_id = config.STEAM_USER_ID if config.STEAM_USER_ID else long_id

        if not short_id and not target_id:
            QMessageBox.warning(self, t('ui.dialogs.error'), t('ui.errors.no_users'))
            self.reload_btn.show()
            return

        display_id = target_id if target_id else short_id
        self.user_label.setText(t('ui.main.user_auto', user_id=display_id))

        config_path = config.get_localconfig_path(short_id)
        self.vdf_parser = LocalConfigParser(config_path)
        if not self.vdf_parser.load():
            QMessageBox.warning(self, t('ui.dialogs.error'), t('ui.errors.localconfig_load_error'))
            self.reload_btn.show()
            return

        # Erstelle GameManager
        self.game_manager = GameManager(
            config.STEAM_API_KEY,
            config.CACHE_DIR,
            config.STEAM_PATH
        )

        # Lade Spiele mit Progress Dialog
        if target_id:
            self._load_games_with_progress(target_id)
        else:
            self._load_games_with_progress(None)

    def _load_games_with_progress(self, user_id: Optional[str]):
        """Lädt Spiele in separatem Thread mit Progress Dialog"""

        # Progress Dialog erstellen
        self.progress_dialog = QProgressDialog(
            t('ui.loading.starting'),
            t('ui.dialogs.cancel'),
            0, 100,
            self
        )
        self.progress_dialog.setWindowTitle(t('ui.loading.title'))
        self.progress_dialog.setWindowModality(Qt.WindowModality.WindowModal)
        self.progress_dialog.setMinimumDuration(0)
        self.progress_dialog.setValue(0)

        # Thread erstellen und starten
        self.load_thread = GameLoadThread(self.game_manager, user_id or "local")
        # noinspection PyUnresolvedReferences
        self.load_thread.progress_update.connect(self._on_load_progress)
        # noinspection PyUnresolvedReferences
        self.load_thread.finished.connect(self._on_load_finished)
        self.load_thread.start()

    def _on_load_progress(self, step: str, current: int, total: int):
        """Progress Update vom Load-Thread"""
        if self.progress_dialog:
            self.progress_dialog.setLabelText(step)
            if total > 0:
                percent = int((current / total) * 100)
                self.progress_dialog.setValue(percent)

    def _on_load_finished(self, success: bool):
        if self.progress_dialog:
            self.progress_dialog.close()
            self.progress_dialog = None

        if not success:
            QMessageBox.warning(self, t('ui.dialogs.error'), t('ui.errors.no_games_found'))
            self.reload_btn.show()
            self.set_status(t('ui.status.load_failed'))
            return  # WICHTIG: Früh abbrechen!

        # NUR wenn erfolgreich:
        if not self.game_manager or not self.game_manager.games:  # NEUE PRÜFUNG
            QMessageBox.warning(self, t('ui.dialogs.error'), t('ui.errors.no_games_found'))
            self.reload_btn.show()
            return

        # Merge mit localconfig & weitere Schritte
        self.game_manager.merge_with_localconfig(self.vdf_parser)
        self.steam_scraper = SteamStoreScraper(config.CACHE_DIR, config.TAGS_LANGUAGE)
        self.appinfo_manager = AppInfoManager(config.STEAM_PATH)
        self.appinfo_manager.load_appinfo()
        self.game_manager.apply_metadata_overrides(self.appinfo_manager)
        self._populate_categories()

        # Status-Nachricht
        status_msg = self.game_manager.get_load_source_message()
        self.set_status(status_msg)
        self.reload_btn.hide()

    def _populate_categories(self):
        if not self.game_manager: return
        categories_data = {}
        all_games = sorted(self.game_manager.get_all_games(), key=lambda g: g.sort_name.lower())
        categories_data[t('ui.categories.all_games')] = all_games
        favorites = sorted(self.game_manager.get_favorites(), key=lambda g: g.sort_name.lower())
        if favorites: categories_data[t('ui.categories.favorites')] = favorites
        uncat = sorted(self.game_manager.get_uncategorized_games(), key=lambda g: g.sort_name.lower())
        if uncat: categories_data[t('ui.categories.uncategorized')] = uncat
        cats = self.game_manager.get_all_categories()
        for cat_name in sorted(cats.keys()):
            if cat_name != 'favorite':
                cat_games = sorted(self.game_manager.get_games_by_category(cat_name), key=lambda g: g.sort_name.lower())
                categories_data[cat_name] = cat_games
        self.tree.populate_categories(categories_data)

    def _on_games_selected(self, games: List[Game]):
        self.selected_games = games
        if len(games) > 1:
            self.set_status(t('ui.status.selected_multiple', count=len(games)))
        elif len(games) == 1:
            self.set_status(t('ui.status.selected', name=games[0].name))

    def on_game_selected(self, game: Game):
        self.selected_game = game
        all_categories = list(self.game_manager.get_all_categories().keys())
        self.details_widget.set_game(game, all_categories)
        if not game.developer:
            if self.game_manager.fetch_game_details(game.app_id):
                self.details_widget.set_game(game, all_categories)

    def _on_category_changed_from_details(self, app_id: str, category: str, checked: bool):
        game = self.game_manager.get_game(app_id)
        if not game: return
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

    def on_game_right_click(self, game: Game, pos):
        menu = QMenu(self)
        menu.addAction(t('ui.game_list.context_menu.view_details'), lambda: self.on_game_selected(game))
        menu.addAction(t('ui.game_list.context_menu.toggle_favorite'), lambda: self.toggle_favorite(game))
        menu.addAction(t('ui.game_list.context_menu.open_store'), lambda: self.open_in_store(game))
        menu.addSeparator()
        if len(self.selected_games) > 1:
            menu.addAction(t('ui.game_list.context_menu.auto_categorize_selected'), self.auto_categorize_selected)
            menu.addSeparator()
        menu.addAction(t('ui.game_list.context_menu.edit_metadata'), lambda: self.edit_game_metadata(game))
        menu.exec(pos)

    def on_category_right_click(self, category: str, pos):
        menu = QMenu(self)

        # Special categories: All Games, Favorites, Uncategorized
        all_games = t('ui.categories.all_games')
        favorites = t('ui.categories.favorites')
        uncategorized = t('ui.categories.uncategorized')

        # Favorites → Kein Kontextmenü
        if category == favorites:
            return

        # All Games & Uncategorized → Nur Auto-Categorize
        if category in [all_games, uncategorized]:
            menu.addAction(t('ui.game_list.context_menu.auto_categorize'),
                           lambda: self.auto_categorize_category(category))
        else:
            # Normale Kategorien → Volle Optionen
            menu.addAction(t('ui.game_list.context_menu.rename'), lambda: self.rename_category(category))
            menu.addAction(t('ui.game_list.context_menu.delete'), lambda: self.delete_category(category))
            menu.addSeparator()
            menu.addAction(t('ui.game_list.context_menu.auto_categorize'),
                           lambda: self.auto_categorize_category(category))

        menu.exec(pos)

    def on_search(self, query):
        if not query:
            self._populate_categories()
            return
        if not self.game_manager: return
        results = [g for g in self.game_manager.get_all_games() if query.lower() in g.name.lower()]
        if results:
            sorted_results = sorted(results, key=lambda g: g.name.lower())
            self.tree.populate_categories({t('ui.status.found_results', count=len(results)): sorted_results})
            self.tree.expandAll()
            self.set_status(t('ui.status.found_results', count=len(results)))
        else:
            self.tree.clear()
            self.set_status(t('ui.status.no_results'))

    def clear_search(self):
        self.search_entry.clear()
        self._populate_categories()

    def toggle_favorite(self, game: Game):
        if game.is_favorite():
            game.categories.remove('favorite')
            self.vdf_parser.remove_app_category(game.app_id, 'favorite')
        else:
            game.categories.append('favorite')
            self.vdf_parser.add_app_category(game.app_id, 'favorite')
        self.vdf_parser.save()
        self._populate_categories()

    @staticmethod
    def open_in_store(game: Game):
        import webbrowser
        webbrowser.open(f"https://store.steampowered.com/app/{game.app_id}")

    def rename_category(self, old_name: str):
        new_name, ok = QInputDialog.getText(self, t('ui.game_list.context_menu.rename'),
                                            t('ui.dialogs.rename_category', old=old_name))
        if ok and new_name and new_name != old_name:
            self.vdf_parser.rename_category(old_name, new_name)
            self.vdf_parser.save()
            self._populate_categories()

    def delete_category(self, category: str):
        reply = QMessageBox.question(self, t('ui.dialogs.confirm_delete_category', name=category),
                                     t('ui.dialogs.confirm_delete_category_msg'))
        if reply == QMessageBox.StandardButton.Yes:
            self.vdf_parser.delete_category(category)
            self.vdf_parser.save()
            self._populate_categories()

    def auto_categorize(self):
        if self.selected_games:
            self._show_auto_categorize_dialog(self.selected_games, None)
        else:
            uncat = self.game_manager.get_uncategorized_games()
            self._show_auto_categorize_dialog(uncat, None)

    def auto_categorize_selected(self):
        if self.selected_games:
            self._show_auto_categorize_dialog(self.selected_games, None)

    def auto_categorize_category(self, category: str):
        """Auto-Categorize für eine bestimmte Kategorie"""
        all_games = t('ui.categories.all_games')
        uncategorized = t('ui.categories.uncategorized')

        # All Games → Alle Spiele
        if category == all_games:
            games = self.game_manager.get_all_games()
            self._show_auto_categorize_dialog(games, category)
        # Uncategorized → Nur unkategorisierte
        elif category == uncategorized:
            games = self.game_manager.get_uncategorized_games()
            self._show_auto_categorize_dialog(games, category)
        # Normale Kategorie
        else:
            games = self.game_manager.get_games_by_category(category)
            self._show_auto_categorize_dialog(games, category)

    def _show_auto_categorize_dialog(self, games: List[Game], category_name: Optional[str]):
        self.dialog_games = games
        dialog = AutoCategorizeDialog(self, games, len(self.game_manager.games),
                                      self._do_auto_categorize, category_name)
        dialog.exec()

    def _do_auto_categorize(self, settings: dict):
        if not settings: return

        if settings['scope'] == 'all':
            games = self.game_manager.get_all_games()
        else:
            games = self.dialog_games if self.dialog_games else self.game_manager.get_uncategorized_games()

        methods = settings['methods']
        progress = QProgressDialog(t('ui.auto_categorize.processing', current=0, total=len(games)),
                                   t('ui.auto_categorize.cancel'), 0, len(methods) * len(games), self)
        progress.setWindowModality(Qt.WindowModality.WindowModal)

        step = 0
        for method in methods:
            if method == 'tags':
                for i, game in enumerate(games):
                    if progress.wasCanceled(): break
                    progress.setValue(step + i)
                    progress.setLabelText(t('ui.auto_categorize.fetching', game=game.name[:50]))
                    QApplication.processEvents()

                    # Fetch all tags (bereits gefiltert nach Blacklist)
                    all_tags = self.steam_scraper.fetch_tags(game.app_id)

                    # Limit to requested count
                    tags = all_tags[:settings['tags_count']]

                    for tag in tags:
                        self.vdf_parser.add_app_category(game.app_id, tag)
                        if tag not in game.categories: game.categories.append(tag)
                step += len(games)

            elif method == 'publisher':
                for game in games:
                    if game.publisher:
                        cat = t('ui.auto_categorize.category_publisher', publisher=game.publisher)
                        self.vdf_parser.add_app_category(game.app_id, cat)
                        if cat not in game.categories: game.categories.append(cat)

            elif method == 'franchise':
                for game in games:
                    franchise = SteamStoreScraper.detect_franchise(game.name)
                    if franchise:
                        cat = t('ui.auto_categorize.category_franchise', franchise=franchise)
                        self.vdf_parser.add_app_category(game.app_id, cat)
                        if cat not in game.categories: game.categories.append(cat)

            elif method == 'genre':
                for game in games:
                    if game.genres:
                        for genre in game.genres:
                            self.vdf_parser.add_app_category(game.app_id, genre)
                            if genre not in game.categories: game.categories.append(genre)

        self.vdf_parser.save()
        progress.close()
        self._populate_categories()
        QMessageBox.information(self, t('ui.dialogs.success'), t('ui.dialogs.categorize_complete', methods=len(methods),
                                                                 backup=t('ui.dialogs.backup_msg')))

    def edit_game_metadata(self, game: Game):
        """Edit single game metadata WITH VDF write support + UX improvements"""
        # Hole aktuelle Metadaten
        meta = self.appinfo_manager.get_app_metadata(game.app_id)

        # FÃ¼lle defaults
        if not meta.get('name'):
            meta['name'] = game.name
        if not meta.get('developer'):
            meta['developer'] = game.developer
        if not meta.get('publisher'):
            meta['publisher'] = game.publisher
        if not meta.get('release_date'):
            meta['release_date'] = game.release_year

        # Hole Original fÃ¼r Visual Comparison
        original_meta = None
        if game.app_id in self.appinfo_manager.modifications:
            original_meta = self.appinfo_manager.modifications[game.app_id].get('original', {})

        if not original_meta:
            # Wenn noch kein Original getrackt, nutze aktuelle Daten
            original_meta = meta.copy()

        # Ã–ffne Dialog mit Original-Daten fÃ¼r Visual Feedback
        dialog = MetadataEditDialog(self, game.name, meta, original_meta)

        if dialog.exec():
            new_meta = dialog.get_metadata()

            if new_meta:
                # Extrahiere write_to_vdf Flag
                write_to_vdf = new_meta.pop('write_to_vdf', False)

                # Setze Metadaten (speichert in custom_metadata.json)
                self.appinfo_manager.set_app_metadata(game.app_id, new_meta)

                # Speichere in JSON
                self.appinfo_manager.save_appinfo()

                # OPTIONAL: In appinfo.vdf schreiben
                if write_to_vdf:
                    progress = QProgressDialog(
                        t('ui.status.writing_vdf'),
                        None, 0, 0, self
                    )
                    progress.setWindowModality(Qt.WindowModality.WindowModal)
                    progress.show()

                    # Lade appinfo
                    self.appinfo_manager.load_appinfo()

                    # Schreibe in VDF
                    success = self.appinfo_manager.write_to_vdf(backup=True)

                    progress.close()

                    if success:
                        # Success Dialog mit Instructions
                        msg = QMessageBox(self)
                        msg.setIcon(QMessageBox.Icon.Information)
                        msg.setWindowTitle(t('ui.metadata_editor.vdf_success_title'))

                        msg.setText(t('ui.metadata_editor.vdf_success_text'))
                        msg.setInformativeText(t('ui.metadata_editor.vdf_success_details'))

                        msg.setStandardButtons(QMessageBox.StandardButton.Ok)
                        msg.exec()

                # Update game object
                if new_meta.get('name'):
                    game.name = new_meta['name']
                if new_meta.get('developer'):
                    game.developer = new_meta['developer']
                if new_meta.get('publisher'):
                    game.publisher = new_meta['publisher']

                # Refresh UI
                self._populate_categories()
                self.on_game_selected(game)

                QMessageBox.information(
                    self,
                    t('ui.dialogs.success'),
                    t('ui.dialogs.metadata_success', name=game.name)
                )

    def bulk_edit_metadata(self):
        if not self.selected_games:
            QMessageBox.warning(self, t('ui.dialogs.no_selection'), t('ui.dialogs.no_games_selected'))
            return
        game_names = [g.name for g in self.selected_games]
        dialog = BulkMetadataEditDialog(self, len(self.selected_games), game_names)
        if dialog.exec():
            settings = dialog.get_metadata()
            if settings:
                self._do_bulk_metadata_edit(self.selected_games, settings)

    def _do_bulk_metadata_edit(self, games: List[Game], settings: Dict):
        """Bulk edit with optional VDF write"""

        # Extrahiere name_modifications
        name_mods = settings.pop('name_modifications', {})

        # Apply to all games
        for game in games:
            # Name modifications
            new_name = game.name
            if name_mods.get('prefix'):
                new_name = name_mods['prefix'] + new_name
            if name_mods.get('suffix'):
                new_name = new_name + name_mods['suffix']
            if name_mods.get('remove'):
                new_name = new_name.replace(name_mods['remove'], '')

            # Setze Metadaten
            meta = settings.copy()
            if new_name != game.name:
                meta['name'] = new_name

            self.appinfo_manager.set_app_metadata(game.app_id, meta)

        # Save to JSON
        self.appinfo_manager.save_appinfo()

        # Ask if write to VDF
        reply = QMessageBox.question(
            self,
            t('ui.metadata_editor.vdf_write_question'),
            t('ui.metadata_editor.bulk_vdf_question', count=len(games)),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            # Load appinfo
            self.appinfo_manager.load_appinfo()

            # Write to VDF
            success = self.appinfo_manager.write_to_vdf(backup=True)

            if success:
                QMessageBox.information(
                    self,
                    t('ui.dialogs.success'),
                    t('ui.metadata_editor.bulk_vdf_success', count=len(games))
                )

        # Update UI
        self._populate_categories()
        QMessageBox.information(
            self,
            t('ui.dialogs.success'),
            t('ui.dialogs.bulk_success', count=len(games))
        )

    def find_missing_metadata(self):
        """Find games with missing metadata (Developer/Publisher/Release)"""
        if not self.game_manager:
            return

        # Find affected games
        affected = []
        for game in self.game_manager.get_all_games():
            # Check if any metadata is missing
            # WICHTIG: Nur als "missing" zählen wenn WIRKLICH leer oder "Unknown"
            has_missing = False

            # Helper function to check if a field is really missing
            def is_missing(value) -> bool:
                if value is None:
                    return True
                value_str = str(value).strip()  # ← Konvertiert int → str
                if not value_str:
                    return True
                if value_str in ["Unknown", "Unbekannt"]:
                    return True
                return False

            # Developer missing?
            if is_missing(game.developer):
                has_missing = True

            # Publisher missing?
            if is_missing(game.publisher):
                has_missing = True

            # Release missing?
            if is_missing(game.release_year):
                has_missing = True

            if has_missing:
                affected.append(game)

        # Show results
        if affected:
            dialog = MissingMetadataDialog(self, affected)
            dialog.exec()
        else:
            # All games have complete metadata!
            QMessageBox.information(
                self,
                t('ui.tools.missing_metadata.no_games_found'),
                t('ui.tools.missing_metadata.no_games_message',
                  count=len(self.game_manager.games))
            )

    def restore_metadata_changes(self):
        """Restore all tracked metadata changes WITH VDF write support"""
        if not self.appinfo_manager:
            return

        mod_count = self.appinfo_manager.get_modification_count()
        if mod_count == 0:
            QMessageBox.information(
                self,
                t('ui.dialogs.no_changes'),
                t('ui.dialogs.no_tracked_changes')
            )
            return

        # Zeige Dialog
        dialog = MetadataRestoreDialog(self, mod_count)
        if dialog.exec() and dialog.should_restore():
            # Progress Dialog
            progress = QProgressDialog(
                t('ui.status.restoring'),
                None, 0, 0, self
            )
            progress.setWindowModality(Qt.WindowModality.WindowModal)
            progress.show()

            try:
                # Restore durchführen (lädt appinfo und schreibt in VDF!)
                restored = self.appinfo_manager.restore_modifications()
                progress.close()

                if restored > 0:
                    QMessageBox.information(
                        self,
                        t('ui.dialogs.success'),
                        t('ui.dialogs.restore_success_with_restart', count=restored)
                    )
                    # Refresh UI
                    self.refresh_data()
                else:
                    QMessageBox.warning(
                        self,
                        t('ui.dialogs.error'),
                        t('ui.dialogs.restore_failed')
                    )
            except Exception as e:
                progress.close()
                QMessageBox.critical(
                    self,
                    t('ui.dialogs.error'),
                    t('ui.dialogs.restore_error', error=str(e))
                )

    def refresh_data(self):
        """Reload Button Action"""
        self._load_data()

    def show_settings(self):
        dialog = SettingsDialog(self)
        # noinspection PyUnresolvedReferences
        dialog.language_changed.connect(self._on_ui_language_changed_live)
        if dialog.exec():
            settings = dialog.get_settings()
            if settings:
                self._apply_settings(settings)

    def _on_ui_language_changed_live(self, new_language: str):
        config.UI_LANGUAGE = new_language
        init_i18n(new_language)
        self._refresh_menubar()
        self._refresh_toolbar()
        self.setWindowTitle(t('ui.main.title'))
        self.set_status(t('ui.status.ready'))

    def _refresh_menubar(self):
        self.menuBar().clear()
        self._create_ui()

    def _apply_settings(self, settings: dict):
        config.UI_LANGUAGE = settings['ui_language']
        config.TAGS_LANGUAGE = settings['tags_language']
        config.TAGS_PER_GAME = settings['tags_per_game']
        config.IGNORE_COMMON_TAGS = settings['ignore_common_tags']
        config.STEAMGRIDDB_API_KEY = settings['steamgriddb_api_key']
        config.MAX_BACKUPS = settings['max_backups']

        if settings.get('steam_api_key'):
            config.STEAM_API_KEY = settings['steam_api_key']

        if settings['steam_path']:
            config.STEAM_PATH = Path(settings['steam_path'])
        if self.steam_scraper:
            self.steam_scraper.set_language(config.TAGS_LANGUAGE)

        self._save_settings(settings)
        QMessageBox.information(
            self,
            t('ui.dialogs.success'),
            t('ui.settings.saved_message', ui=settings['ui_language'], tags=settings['tags_language'])
        )

    @staticmethod
    def _save_settings(settings: dict):
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

    def set_status(self, text: str):
        self.statusbar.showMessage(text)