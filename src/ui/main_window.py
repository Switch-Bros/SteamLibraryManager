"""
Main Window - Strings Localized
Speichern als: src/ui/main_window.py
"""
# ... (Imports wie gehabt)
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLineEdit, QPushButton, QLabel, QToolBar, QMenu,
    QMessageBox, QInputDialog, QSplitter, QCheckBox,
    QFrame, QProgressDialog, QApplication
)
from PyQt6.QtCore import Qt, QUrl
from PyQt6.QtGui import QAction, QDesktopServices
from typing import Optional, List, Dict
from pathlib import Path
from datetime import datetime

from src.config import config
from src.core.game_manager import GameManager, Game
from src.core.localconfig_parser import LocalConfigParser
from src.core.appinfo_manager import AppInfoManager
from src.core.steam_auth import SteamAuthManager
from src.integrations.steam_store import SteamStoreScraper, FranchiseDetector
from src.ui.auto_categorize_dialog import AutoCategorizeDialog
from src.ui.metadata_dialogs import (
    MetadataEditDialog,
    BulkMetadataEditDialog,
    MetadataRestoreDialog
)
from src.utils.i18n import t, init_i18n
from src.ui.settings_dialog import SettingsDialog
from src.ui.game_details_widget import GameDetailsWidget
from src.ui.components.category_tree import GameTreeWidget


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(t('ui.main.title'))
        self.resize(1400, 800)

        self.game_manager: Optional[GameManager] = None
        self.vdf_parser: Optional[LocalConfigParser] = None
        self.steam_scraper: Optional[SteamStoreScraper] = None
        self.appinfo_manager: Optional[AppInfoManager] = None

        self.auth_manager = SteamAuthManager()
        self.auth_manager.auth_success.connect(self._on_steam_login_success)
        self.auth_manager.auth_error.connect(self._on_steam_login_error)

        self.selected_game: Optional[Game] = None
        self.selected_games: List[Game] = []
        self.dialog_games: List[Game] = []

        self._create_ui()
        self._load_data()

    def _create_ui(self):
        menubar = self.menuBar()

        # 1. FILE
        file_menu = menubar.addMenu(t('ui.menu.file'))
        file_menu.addAction(QAction(t('ui.menu.refresh'), self, triggered=self.refresh_data))
        file_menu.addAction(QAction(t('ui.menu.save'), self, triggered=self.force_save))
        file_menu.addSeparator()
        file_menu.addAction(QAction(t('ui.menu.exit'), self, triggered=self.close))

        # 2. EDIT
        edit_menu = menubar.addMenu(t('ui.menu.edit'))
        edit_menu.addAction(QAction(t('ui.menu.bulk_edit'), self, triggered=self.bulk_edit_metadata))
        edit_menu.addAction(QAction(t('ui.toolbar.auto_categorize'), self, triggered=self.auto_categorize))

        # 3. SETTINGS
        settings_menu = menubar.addMenu(t('ui.toolbar.settings'))
        settings_menu.addAction(QAction(t('ui.menu.settings'), self, triggered=self.show_settings))
        settings_menu.addSeparator()
        settings_menu.addAction(QAction(t('ui.menu.restore'), self, triggered=self.restore_metadata_changes))

        # 4. HELP
        help_menu = menubar.addMenu(t('ui.menu.help'))
        github_action = QAction(t('ui.menu.github'), self)
        github_action.triggered.connect(lambda: QDesktopServices.openUrl(QUrl("https://github.com/")))
        help_menu.addAction(github_action)

        check_updates = QAction(t('ui.menu.check_updates'), self)
        help_menu.addAction(check_updates)

        donate_action = QAction(t('ui.menu.donate'), self)
        donate_action.triggered.connect(lambda: QDesktopServices.openUrl(QUrl("https://paypal.me/DeinAccount")))
        help_menu.addAction(donate_action)

        help_menu.addSeparator()
        help_menu.addAction(QAction(t('ui.menu.about'), self, triggered=self.show_about))

        self.user_label = QLabel(t('ui.status.not_logged_in'))
        self.user_label.setStyleSheet("padding: 5px 10px;")
        menubar.setCornerWidget(self.user_label, Qt.Corner.TopRightCorner)

        self.toolbar = QToolBar()
        self.addToolBar(self.toolbar)
        self._refresh_toolbar()

        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(5, 5, 5, 5)

        splitter = QSplitter(Qt.Orientation.Horizontal)

        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(2)

        search_layout = QHBoxLayout()
        search_layout.addWidget(QLabel(t('ui.main.search_icon')))
        self.search_entry = QLineEdit()
        self.search_entry.setPlaceholderText(t('ui.main.search_placeholder'))
        self.search_entry.textChanged.connect(self.on_search)
        search_layout.addWidget(self.search_entry)
        clear_btn = QPushButton("×")
        clear_btn.clicked.connect(self.clear_search)
        clear_btn.setMaximumWidth(30)
        search_layout.addWidget(clear_btn)
        left_layout.addLayout(search_layout)

        btn_layout = QHBoxLayout()
        expand_btn = QPushButton(t('ui.categories.sym_expand') + " " + t('ui.main.expand_all'))
        expand_btn.clicked.connect(lambda: self.tree.expandAll())
        btn_layout.addWidget(expand_btn)

        collapse_btn = QPushButton(t('ui.categories.sym_collapse') + " " + t('ui.main.collapse_all'))
        collapse_btn.clicked.connect(lambda: self.tree.collapseAll())
        btn_layout.addWidget(collapse_btn)
        left_layout.addLayout(btn_layout)

        self.tree = GameTreeWidget()
        self.tree.game_clicked.connect(self.on_game_selected)
        self.tree.game_right_clicked.connect(self.on_game_right_click)
        self.tree.category_right_clicked.connect(self.on_category_right_click)
        self.tree.selection_changed.connect(self._on_games_selected)
        left_layout.addWidget(self.tree)

        splitter.addWidget(left_widget)

        self.details_widget = GameDetailsWidget()
        self.details_widget.category_changed.connect(self._on_category_changed_from_details)
        self.details_widget.edit_metadata.connect(self.edit_game_metadata)
        splitter.addWidget(self.details_widget)

        splitter.setSizes([350, 1050])
        layout.addWidget(splitter)

        self.statusbar = self.statusBar()
        self.set_status(t('ui.status.ready'))

    def _refresh_toolbar(self):
        self.toolbar.clear()
        self.toolbar.addAction(t('ui.toolbar.refresh'), self.refresh_data)
        self.toolbar.addAction(t('ui.toolbar.auto_categorize'), self.auto_categorize)
        self.toolbar.addSeparator()
        self.toolbar.addAction(t('ui.toolbar.settings'), self.show_settings)
        self.toolbar.addSeparator()

        login_action = QAction(t('ui.toolbar.login'), self)
        login_action.triggered.connect(self._start_steam_login)
        self.toolbar.addAction(login_action)

    def _start_steam_login(self):
        QMessageBox.information(self, t('ui.login.title'), t('ui.login.info'))
        self.auth_manager.start_login()
        self.set_status(t('ui.login.status_waiting'))

    def _on_steam_login_success(self, code: str):
        # TODO: Token Swap logic here
        print(f"Auth Code: {code}")
        self.set_status(t('ui.login.status_success'))
        QMessageBox.information(self, t('ui.login.title'), t('ui.login.status_success'))

    def _on_steam_login_error(self, error: str):
        self.set_status(t('ui.login.status_failed'))
        QMessageBox.critical(self, t('ui.dialogs.error'), error)

    def force_save(self):
        if self.vdf_parser:
            if self.vdf_parser.save():
                self.set_status(t('ui.status.saved_backup'))
            else:
                QMessageBox.critical(self, t('ui.dialogs.error'), t('ui.errors.save_failed'))

    def show_about(self):
        QMessageBox.about(self, t('ui.menu.about'), t('ui.dialogs.about_text'))

    def _load_data(self):
        self.set_status(t('ui.status.loading'))
        if not config.STEAM_PATH:
            QMessageBox.warning(self, t('ui.dialogs.error'), t('errors.steam_not_found'))
            return
        short_id, long_id = config.get_detected_user()
        if not short_id:
            QMessageBox.warning(self, t('ui.dialogs.error'), t('ui.errors.no_users'))
            return
        self.user_label.setText(t('ui.main.user_auto', user_id=short_id))
        config_path = config.get_localconfig_path(short_id)
        self.vdf_parser = LocalConfigParser(config_path)
        if not self.vdf_parser.load():
            QMessageBox.warning(self, t('ui.dialogs.error'), t('ui.errors.localconfig_load_error'))
            return
        self.game_manager = GameManager(config.STEAM_API_KEY, config.CACHE_DIR)
        api_success = self.game_manager.load_from_steam_api(long_id)
        if not api_success:
            # FIX: Offline Message Localized
            self.set_status(t('ui.status.api_error') + t('ui.status.offline_mode'))
        self.game_manager.merge_with_localconfig(self.vdf_parser)
        self.steam_scraper = SteamStoreScraper(config.CACHE_DIR, config.TAGS_LANGUAGE)
        self.appinfo_manager = AppInfoManager(config.STEAM_PATH)
        self.appinfo_manager.load_appinfo()
        self.game_manager.apply_metadata_overrides(self.appinfo_manager)
        self._populate_categories()
        if api_success:
            self.set_status(t('ui.status.loaded', count=len(self.game_manager.games)))
        else:
            # FIX: Offline Message Localized
            self.set_status(t('ui.status.loaded', count=len(self.game_manager.games)) + t('ui.status.offline_mode'))

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
        special = [t('ui.categories.all_games'), t('ui.categories.favorites'), t('ui.categories.uncategorized')]
        if category in special: return
        menu = QMenu(self)
        menu.addAction(t('ui.game_list.context_menu.rename'), lambda: self.rename_category(category))
        menu.addAction(t('ui.game_list.context_menu.delete'), lambda: self.delete_category(category))
        menu.addSeparator()
        menu.addAction(t('ui.game_list.context_menu.auto_categorize'), lambda: self.auto_categorize_category(category))
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

    def open_in_store(self, game: Game):
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
                    tags = self.steam_scraper.get_game_tags(game.app_id, settings['tags_count'],
                                                            settings['ignore_common'])
                    for tag in tags:
                        self.vdf_parser.add_app_category(game.app_id, tag)
                        if tag not in game.categories: game.categories.append(tag)
                step += len(games)
            elif method == 'publisher':
                for game in games:
                    if game.publisher:
                        cat = f"Publisher: {game.publisher}"
                        self.vdf_parser.add_app_category(game.app_id, cat)
                        if cat not in game.categories: game.categories.append(cat)
            elif method == 'franchise':
                for game in games:
                    franchise = FranchiseDetector.detect_franchise(game.name)
                    if franchise:
                        cat = f"Franchise: {franchise}"
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
        # FIX: Backup Message Localized
        QMessageBox.information(self, t('ui.dialogs.success'), t('ui.dialogs.categorize_complete', methods=len(methods),
                                                                 backup=t('ui.dialogs.backup_msg')))

    def edit_game_metadata(self, game: Game):
        meta = self.appinfo_manager.get_app_metadata(game.app_id)
        if not meta.get('name'): meta['name'] = game.name
        if not meta.get('developer'): meta['developer'] = game.developer
        if not meta.get('publisher'): meta['publisher'] = game.publisher
        if not meta.get('release_date'): meta['release_date'] = game.release_year
        dialog = MetadataEditDialog(self, game.name, meta)
        if dialog.exec():
            new_meta = dialog.get_metadata()
            if new_meta:
                self.appinfo_manager.set_app_metadata(game.app_id, new_meta)
                self.appinfo_manager.save_appinfo()
                if new_meta.get('name'): game.name = new_meta['name']
                if new_meta.get('developer'): game.developer = new_meta['developer']
                if new_meta.get('publisher'): game.publisher = new_meta['publisher']
                self._populate_categories()
                self.on_game_selected(game)
                QMessageBox.information(self, t('ui.dialogs.success'), t('ui.dialogs.metadata_success', name=game.name))

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
        progress = QProgressDialog(t('ui.status.applying_changes'), t('ui.dialogs.cancel'), 0, len(games), self)
        progress.setWindowModality(Qt.WindowModality.WindowModal)
        success_count = 0
        for i, game in enumerate(games):
            if progress.wasCanceled(): break
            progress.setValue(i)
            progress.setLabelText(f"{game.name[:50]}...")
            QApplication.processEvents()
            meta = self.appinfo_manager.get_app_metadata(game.app_id)
            modified_meta = meta.copy()
            if 'developer' in settings: modified_meta['developer'] = settings['developer']
            if 'publisher' in settings: modified_meta['publisher'] = settings['publisher']
            if 'release_date' in settings: modified_meta['release_date'] = settings['release_date']
            if 'name_modifications' in settings:
                name_mods = settings['name_modifications']
                name = modified_meta.get('name', game.name)
                if 'remove' in name_mods and name_mods['remove']:
                    name = name.replace(name_mods['remove'], '')
                if 'prefix' in name_mods and name_mods['prefix']:
                    name = name_mods['prefix'] + name
                if 'suffix' in name_mods and name_mods['suffix']:
                    name = name + name_mods['suffix']
                modified_meta['name'] = name.strip()
            self.appinfo_manager.set_app_metadata(game.app_id, modified_meta)
            success_count += 1
        progress.setValue(len(games))
        if success_count > 0:
            self.appinfo_manager.save_appinfo()
            self.game_manager.apply_metadata_overrides(self.appinfo_manager)
            self._populate_categories()
            QMessageBox.information(self, t('ui.dialogs.success'), t('ui.dialogs.bulk_success', count=success_count))

    def restore_metadata_changes(self):
        if not self.appinfo_manager: return
        mod_count = self.appinfo_manager.get_modification_count()
        if mod_count == 0:
            QMessageBox.information(self, t('ui.dialogs.no_changes'), t('ui.dialogs.no_tracked_changes'))
            return
        dialog = MetadataRestoreDialog(self, mod_count)
        if dialog.exec() and dialog.should_restore():
            restored = self.appinfo_manager.restore_modifications()
            self.appinfo_manager.save_appinfo()
            self.refresh_data()
            QMessageBox.information(self, t('ui.dialogs.success'), t('ui.dialogs.restore_success', count=restored))

    def refresh_data(self):
        self._load_data()

    def show_settings(self):
        dialog = SettingsDialog(self)
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

    def _save_settings(self, settings: dict):
        import json
        settings_file = config.DATA_DIR / 'settings.json'
        data = {
            'ui_language': settings['ui_language'],
            'tags_language': settings['tags_language'],
            'tags_per_game': settings['tags_per_game'],
            'ignore_common_tags': settings['ignore_common_tags'],
            'steamgriddb_api_key': settings['steamgriddb_api_key'],
            'max_backups': settings['max_backups']
        }
        with open(settings_file, 'w') as f:
            json.dump(data, f, indent=2)

    def set_status(self, text: str):
        self.statusbar.showMessage(text)