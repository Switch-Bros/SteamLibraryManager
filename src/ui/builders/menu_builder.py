# src/ui/builders/menu_builder.py

"""Builder for the main application menu bar.

Constructs a rich, Steam-inspired menu bar with submenus, filters,
and stub entries for future features. Each top-level menu is built
by a dedicated private method for maintainability.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from PyQt6.QtCore import Qt, QUrl
from PyQt6.QtGui import QAction, QActionGroup, QDesktopServices
from PyQt6.QtWidgets import QMenuBar, QLabel

from src.utils.i18n import t

if TYPE_CHECKING:
    from src.ui.main_window import MainWindow

__all__ = ["MenuBuilder"]

_GITHUB_URL = "https://github.com/Switch-Bros/SteamLibraryManager"


class MenuBuilder:
    """Constructs the entire QMenuBar for the application.

    Owns no state beyond a reference to MainWindow. All menu actions
    connect directly to MainWindow methods so that signal routing is
    unchanged after extraction.

    Attributes:
        main_window: Back-reference to the owning MainWindow instance.
        user_label: The corner-widget label that displays the logged-in user.
    """

    def __init__(self, main_window: MainWindow) -> None:
        """Initializes the MenuBuilder.

        Args:
            main_window: The MainWindow instance that owns this menu bar.
        """
        self.main_window: MainWindow = main_window
        self.user_label: QLabel = QLabel(t("common.unknown"))

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def build(self, menubar: QMenuBar) -> None:
        """Populates an existing QMenuBar with all application menus.

        This is called on the menubar returned by QMainWindow.menuBar() so
        that Qt's native menu integration is preserved.

        Args:
            menubar: The QMenuBar instance to populate.
        """
        self._build_file_menu(menubar)
        self._build_edit_menu(menubar)
        self._build_view_menu(menubar)
        self._build_tools_menu(menubar)
        self._build_help_menu(menubar)
        self._attach_corner_widget(menubar)

    # ------------------------------------------------------------------
    # Private – Helper methods
    # ------------------------------------------------------------------

    def _not_implemented(self, feature_key: str) -> None:
        """Shows a placeholder message in the status bar for unfinished features.

        Args:
            feature_key: The i18n key whose translated value is used as
                the feature name in the placeholder message.
        """
        feature = t(feature_key)
        msg = f"{t('common.placeholder_message', feature=feature)} {t('emoji.rocket')}"
        self.main_window.set_status(msg)

    def _open_url(self, url: str) -> None:
        """Opens a URL in the default system browser.

        Args:
            url: The URL to open.
        """
        QDesktopServices.openUrl(QUrl(url))

    def _edit_single_game(self) -> None:
        """Selection guard for single game metadata editing.

        Checks whether a game is selected; if not, shows a status bar
        message. Otherwise delegates to EditActions.
        """
        mw = self.main_window
        if mw.selected_game is None:
            mw.set_status(t("ui.errors.no_selection"))
            return
        mw.edit_actions.edit_game_metadata(mw.selected_game)

    def _rename_selected_collection(self) -> None:
        """Selection guard for collection renaming.

        Checks whether a category is selected; if not, shows a status
        bar message. Currently a stub after the guard passes.
        """
        mw = self.main_window
        selected = mw.tree.get_selected_categories()
        if not selected:
            mw.set_status(t("ui.errors.no_selection"))
            return
        self._not_implemented("menu.edit.collections.rename")

    def _merge_selected_collections(self) -> None:
        """Selection guard for merging multiple collections.

        Checks whether at least two categories are selected; if not,
        shows a status bar message. Currently a stub after the guard passes.
        """
        mw = self.main_window
        selected = mw.tree.get_selected_categories()
        if len(selected) < 2:
            mw.set_status(t("ui.errors.no_selection"))
            return
        self._not_implemented("menu.edit.collections.merge")

    # ------------------------------------------------------------------
    # Private – one method per top-level menu
    # ------------------------------------------------------------------

    def _build_file_menu(self, menubar: QMenuBar) -> None:
        """Builds the File menu: Refresh, Save, Export, Import, Exit.

        Args:
            menubar: The parent menu bar to add the menu to.
        """
        mw = self.main_window
        file_menu = menubar.addMenu(t("menu.file.root"))

        # Refresh
        refresh_action = QAction(t("menu.file.refresh"), mw)
        refresh_action.triggered.connect(mw.file_actions.refresh_data)
        file_menu.addAction(refresh_action)

        # Save
        save_action = QAction(t("common.save"), mw)
        save_action.triggered.connect(mw.file_actions.force_save)
        file_menu.addAction(save_action)

        file_menu.addSeparator()

        # Export submenu
        export_menu = file_menu.addMenu(t("menu.file.export.root"))

        # Collections as VDF (wired to file_actions)
        export_vdf_action = QAction(t("menu.file.export.collections_vdf"), mw)
        export_vdf_action.triggered.connect(mw.file_actions.export_collections_text)
        export_menu.addAction(export_vdf_action)

        # Collections as human-readable text (wired)
        export_text_action = QAction(t("menu.file.export.collections_text"), mw)
        export_text_action.triggered.connect(mw.file_actions.export_collections_text)
        export_menu.addAction(export_text_action)

        # CSV Simple (wired)
        export_csv_simple_action = QAction(t("menu.file.export.games_csv_simple"), mw)
        export_csv_simple_action.triggered.connect(mw.file_actions.export_csv_simple)
        export_menu.addAction(export_csv_simple_action)

        # CSV Full (wired)
        export_csv_full_action = QAction(t("menu.file.export.games_csv_full"), mw)
        export_csv_full_action.triggered.connect(mw.file_actions.export_csv_full)
        export_menu.addAction(export_csv_full_action)

        # JSON (wired)
        export_json_action = QAction(t("menu.file.export.games_json"), mw)
        export_json_action.triggered.connect(mw.file_actions.export_json)
        export_menu.addAction(export_json_action)

        # Artwork Package (stub — Phase 6/7)
        export_artwork_action = QAction(t("menu.file.export.artwork_package"), mw)
        export_artwork_action.triggered.connect(lambda: self._not_implemented("menu.file.export.artwork_package"))
        export_menu.addAction(export_artwork_action)

        # DB Backup (wired)
        export_db_action = QAction(t("menu.file.export.db_backup"), mw)
        export_db_action.triggered.connect(mw.file_actions.export_db_backup)
        export_menu.addAction(export_db_action)

        # Import submenu
        import_menu = file_menu.addMenu(t("menu.file.import.root"))

        # Collections VDF (wired)
        import_coll_action = QAction(t("menu.file.import.collections"), mw)
        import_coll_action.triggered.connect(mw.file_actions.import_collections_vdf)
        import_menu.addAction(import_coll_action)

        # DB Backup (wired)
        import_db_action = QAction(t("menu.file.import.db_backup"), mw)
        import_db_action.triggered.connect(mw.file_actions.import_db_backup)
        import_menu.addAction(import_db_action)

        # Artwork Package (stub — Phase 6/7)
        import_artwork_action = QAction(t("menu.file.import.artwork_package"), mw)
        import_artwork_action.triggered.connect(lambda: self._not_implemented("menu.file.import.artwork_package"))
        import_menu.addAction(import_artwork_action)

        # --- Profiles submenu ---
        profiles_menu = file_menu.addMenu(t("menu.file.profiles.root"))

        save_profile = QAction(t("menu.file.profiles.save_current"), mw)
        save_profile.triggered.connect(mw.profile_actions.save_current_as_profile)
        profiles_menu.addAction(save_profile)

        manage_profiles = QAction(t("menu.file.profiles.manage"), mw)
        manage_profiles.triggered.connect(mw.profile_actions.show_profile_manager)
        profiles_menu.addAction(manage_profiles)

        file_menu.addSeparator()

        # Exit
        exit_action = QAction(t("menu.file.exit"), mw)
        exit_action.triggered.connect(mw.file_actions.exit_application)
        file_menu.addAction(exit_action)

    def _build_edit_menu(self, menubar: QMenuBar) -> None:
        """Builds the Edit menu: Metadata, Auto-Cat, Collections, etc.

        Args:
            menubar: The parent menu bar to add the menu to.
        """
        mw = self.main_window
        edit_menu = menubar.addMenu(t("menu.edit.root"))

        # --- Metadata submenu ---
        metadata_menu = edit_menu.addMenu(t("menu.edit.metadata.root"))

        single_action = QAction(t("menu.edit.metadata.single"), mw)
        single_action.triggered.connect(self._edit_single_game)
        metadata_menu.addAction(single_action)

        bulk_action = QAction(t("menu.edit.metadata.bulk"), mw)
        bulk_action.triggered.connect(mw.edit_actions.bulk_edit_metadata)
        metadata_menu.addAction(bulk_action)

        # Auto-Categorize
        auto_cat_action = QAction(t("menu.edit.auto_categorize"), mw)
        auto_cat_action.triggered.connect(mw.edit_actions.auto_categorize)
        edit_menu.addAction(auto_cat_action)

        edit_menu.addSeparator()

        # --- Collections submenu ---
        collections_menu = edit_menu.addMenu(t("menu.edit.collections.root"))

        rename_action = QAction(t("menu.edit.collections.rename"), mw)
        rename_action.triggered.connect(self._rename_selected_collection)
        collections_menu.addAction(rename_action)

        merge_action = QAction(t("menu.edit.collections.merge"), mw)
        merge_action.triggered.connect(self._merge_selected_collections)
        collections_menu.addAction(merge_action)

        delete_empty_action = QAction(t("menu.edit.collections.delete_empty"), mw)
        delete_empty_action.triggered.connect(lambda: self._not_implemented("menu.edit.collections.delete_empty"))
        collections_menu.addAction(delete_empty_action)

        collections_menu.addSeparator()

        expand_action = QAction(t("menu.edit.collections.expand_all"), mw)
        expand_action.triggered.connect(mw.view_actions.expand_all)
        collections_menu.addAction(expand_action)

        collapse_action = QAction(t("menu.edit.collections.collapse_all"), mw)
        collapse_action.triggered.connect(mw.view_actions.collapse_all)
        collections_menu.addAction(collapse_action)

        edit_menu.addSeparator()

        # Find Missing Metadata
        find_missing_action = QAction(t("menu.edit.find_missing_metadata"), mw)
        find_missing_action.triggered.connect(mw.tools_actions.find_missing_metadata)
        edit_menu.addAction(find_missing_action)

        # Reset Metadata
        reset_action = QAction(t("menu.edit.reset_metadata"), mw)
        reset_action.triggered.connect(mw.edit_actions.restore_metadata_changes)
        edit_menu.addAction(reset_action)

        # Remove Duplicates
        remove_dupes_action = QAction(t("menu.edit.remove_duplicates"), mw)
        remove_dupes_action.triggered.connect(mw.file_actions.remove_duplicate_collections)
        edit_menu.addAction(remove_dupes_action)

    def _build_view_menu(self, menubar: QMenuBar) -> None:
        """Builds the View menu: View Mode, Type/Platform/Status filters, Statistics.

        View Mode uses an exclusive QActionGroup (radio-button style).
        Type and Platform filters default to all checked.
        Status filters default to all unchecked.
        All filter actions are currently UI-only stubs.

        Args:
            menubar: The parent menu bar to add the menu to.
        """
        mw = self.main_window
        view_menu = menubar.addMenu(t("menu.view.root"))

        # --- Sort submenu (exclusive radio-button group) ---
        sort_menu = view_menu.addMenu(t("menu.view.sort.root"))
        sort_group = QActionGroup(mw)
        sort_group.setExclusive(True)

        for key in ("name", "playtime", "last_played", "release_date"):
            action = QAction(t(f"menu.view.sort.{key}"), mw)
            action.setCheckable(True)
            if key == "name":
                action.setChecked(True)
            action.triggered.connect(lambda checked, k=key: mw.view_actions.on_sort_changed(k))
            sort_group.addAction(action)
            sort_menu.addAction(action)

        view_menu.addSeparator()

        # --- Type filter submenu (all checked by default) ---
        type_menu = view_menu.addMenu(t("menu.view.type.root"))
        for key in ("games", "soundtracks", "software", "videos", "dlcs", "tools"):
            action = QAction(t(f"menu.view.type.{key}"), mw)
            action.setCheckable(True)
            action.setChecked(True)
            action.triggered.connect(lambda checked, k=key: mw.view_actions.on_filter_toggled("type", k, checked))
            type_menu.addAction(action)

        # --- Platform filter submenu (all checked by default) ---
        platform_menu = view_menu.addMenu(t("menu.view.platform.root"))
        for key in ("linux", "windows", "steamos"):
            action = QAction(t(f"menu.view.platform.{key}"), mw)
            action.setCheckable(True)
            action.setChecked(True)
            action.triggered.connect(lambda checked, k=key: mw.view_actions.on_filter_toggled("platform", k, checked))
            platform_menu.addAction(action)

        # --- Status filter submenu (all unchecked by default) ---
        status_menu = view_menu.addMenu(t("menu.view.status.root"))
        for key in (
            "installed",
            "not_installed",
            "hidden",
            "with_playtime",
            "favorites",
        ):
            action = QAction(t(f"menu.view.status.{key}"), mw)
            action.setCheckable(True)
            action.triggered.connect(lambda checked, k=key: mw.view_actions.on_filter_toggled("status", k, checked))
            status_menu.addAction(action)

        # --- Language filter submenu (all unchecked by default = no filtering) ---
        language_menu = view_menu.addMenu(t("menu.view.language.root"))
        for key in (
            "english",
            "german",
            "french",
            "spanish",
            "italian",
            "portuguese",
            "russian",
            "polish",
            "japanese",
            "chinese_simplified",
            "chinese_traditional",
            "korean",
            "dutch",
            "swedish",
            "turkish",
        ):
            action = QAction(t(f"menu.view.language.{key}"), mw)
            action.setCheckable(True)
            action.triggered.connect(lambda checked, k=key: mw.view_actions.on_filter_toggled("language", k, checked))
            language_menu.addAction(action)

        view_menu.addSeparator()

        # --- Statistics (single action, opens tabbed dialog) ---
        stats_action = QAction(t("menu.view.statistics.root"), mw)
        stats_action.triggered.connect(mw.view_actions.show_statistics)
        view_menu.addAction(stats_action)

    def _build_tools_menu(self, menubar: QMenuBar) -> None:
        """Builds the Tools menu: Artwork, Search, Batch, Database, Settings.

        Settings is the only wired action; all others are stubs.

        Args:
            menubar: The parent menu bar to add the menu to.
        """
        mw = self.main_window
        tools_menu = menubar.addMenu(t("menu.tools.root"))

        # --- Artwork submenu ---
        artwork_menu = tools_menu.addMenu(t("menu.tools.artwork.root"))
        for key in ("download_missing", "edit"):
            action = QAction(t(f"menu.tools.artwork.{key}"), mw)
            action.triggered.connect(lambda checked, k=f"menu.tools.artwork.{key}": self._not_implemented(k))
            artwork_menu.addAction(action)

        # --- Advanced Search submenu ---
        search_menu = tools_menu.addMenu(t("menu.tools.search.root"))
        for key in ("by_publisher", "by_developer", "by_genre", "by_tags", "by_year"):
            action = QAction(t(f"menu.tools.search.{key}"), mw)
            action.triggered.connect(lambda checked, k=f"menu.tools.search.{key}": self._not_implemented(k))
            search_menu.addAction(action)

        # --- Batch Operations submenu ---
        batch_menu = tools_menu.addMenu(t("menu.tools.batch.root"))

        # Update Metadata (wired to enrichment)
        update_meta_action = QAction(t("menu.tools.batch.update_metadata"), mw)
        update_meta_action.triggered.connect(mw.enrichment_actions.start_steam_api_enrichment)
        batch_menu.addAction(update_meta_action)

        # Update HLTB (wired to enrichment)
        update_hltb_action = QAction(t("menu.tools.batch.update_hltb"), mw)
        update_hltb_action.triggered.connect(mw.enrichment_actions.start_hltb_enrichment)
        batch_menu.addAction(update_hltb_action)

        # Remaining batch stubs
        for key in (
            "update_protondb",
            "check_store",
            "update_achievements",
        ):
            action = QAction(t(f"menu.tools.batch.{key}"), mw)
            action.triggered.connect(lambda checked, k=f"menu.tools.batch.{key}": self._not_implemented(k))
            batch_menu.addAction(action)

        # --- Database submenu ---
        db_menu = tools_menu.addMenu(t("menu.tools.database.root"))
        for key in ("optimize", "recreate", "import_appinfo", "backup"):
            action = QAction(t(f"menu.tools.database.{key}"), mw)
            action.triggered.connect(lambda checked, k=f"menu.tools.database.{key}": self._not_implemented(k))
            db_menu.addAction(action)

        tools_menu.addSeparator()

        # Settings (wired action)
        settings_action = QAction(t("menu.tools.settings"), mw)
        settings_action.triggered.connect(mw.settings_actions.show_settings)
        tools_menu.addAction(settings_action)

    def _build_help_menu(self, menubar: QMenuBar) -> None:
        """Builds the Help menu: Docs, Online, Updates, Support, About.

        Online and Support items open URLs in the browser.
        About is wired to SteamActions. Everything else is a stub.

        Args:
            menubar: The parent menu bar to add the menu to.
        """
        mw = self.main_window
        help_menu = menubar.addMenu(t("menu.help.root"))

        # --- Documentation submenu ---
        docs_menu = help_menu.addMenu(t("menu.help.docs.root"))
        for key in ("manual", "tips", "shortcuts"):
            action = QAction(t(f"menu.help.docs.{key}"), mw)
            action.triggered.connect(lambda checked, k=f"menu.help.docs.{key}": self._not_implemented(k))
            docs_menu.addAction(action)

        # --- Online submenu ---
        online_menu = help_menu.addMenu(t("menu.help.online.root"))
        online_urls = {
            "github": _GITHUB_URL,
            "issues": f"{_GITHUB_URL}/issues",
            "discussions": f"{_GITHUB_URL}/discussions",
            "wiki": f"{_GITHUB_URL}/wiki",
        }
        for key, url in online_urls.items():
            action = QAction(t(f"menu.help.online.{key}"), mw)
            action.triggered.connect(lambda checked, u=url: self._open_url(u))
            online_menu.addAction(action)

        # --- Updates submenu ---
        updates_menu = help_menu.addMenu(t("menu.help.updates.root"))
        for key in ("check", "changelog"):
            action = QAction(t(f"menu.help.updates.{key}"), mw)
            action.triggered.connect(lambda checked, k=f"menu.help.updates.{key}": self._not_implemented(k))
            updates_menu.addAction(action)

        # --- Support submenu ---
        support_menu = help_menu.addMenu(t("menu.help.support.root"))
        support_urls = {
            "paypal": "https://paypal.me/",
            "github": "https://github.com/sponsors/Switch-Bros",
            "kofi": "https://ko-fi.com/",
        }
        for key, url in support_urls.items():
            action = QAction(t(f"menu.help.support.{key}"), mw)
            action.triggered.connect(lambda checked, u=url: self._open_url(u))
            support_menu.addAction(action)

        help_menu.addSeparator()

        # About (wired action)
        about_action = QAction(t("menu.help.about"), mw)
        about_action.triggered.connect(mw.steam_actions.show_about)
        help_menu.addAction(about_action)

    def _attach_corner_widget(self, menubar: QMenuBar) -> None:
        """Attaches the user-info label to the top-right corner of the menu bar.

        Args:
            menubar: The menu bar to attach the corner widget to.
        """
        self.user_label.setStyleSheet("padding: 5px 10px;")
        self.user_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.user_label.setMinimumWidth(250)
        menubar.setCornerWidget(self.user_label, Qt.Corner.TopRightCorner)
