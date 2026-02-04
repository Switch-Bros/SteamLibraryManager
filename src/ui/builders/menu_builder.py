# src/ui/builders/menu_builder.py

"""
Builder for the main application menu bar.

Extracts all QMenuBar construction logic from MainWindow._create_ui(),
keeping the same menu structure, t() keys, and signal connections.
"""

from __future__ import annotations
from typing import TYPE_CHECKING

from PyQt6.QtCore import Qt, QUrl
from PyQt6.QtGui import QAction, QDesktopServices
from PyQt6.QtWidgets import QMenuBar, QLabel

from src.utils.i18n import t

if TYPE_CHECKING:
    from src.ui.main_window import MainWindow


class MenuBuilder:
    """Constructs the entire QMenuBar for the application.

    Owns no state beyond a reference to MainWindow. All menu actions
    connect directly to MainWindow methods so that signal routing is
    unchanged after extraction.

    Attributes:
        main_window: Back-reference to the owning MainWindow instance.
        user_label: The corner-widget label that displays the logged-in user.
    """

    def __init__(self, main_window: 'MainWindow') -> None:
        """Initializes the MenuBuilder.

        Args:
            main_window: The MainWindow instance that owns this menu bar.
        """
        self.main_window: 'MainWindow' = main_window
        # Kept as attribute so MainWindow can update it after login
        self.user_label: QLabel = QLabel(t('common.unknown'))

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def build(self, menubar: QMenuBar) -> None:
        """Populates an existing QMenuBar with all application menus.

        This is called on the menubar returned by QMainWindow.menuBar() so
        that Qt's native menu integration is preserved.

        Args:
            menubar: The QMenuBar instance to populate (typically self.menuBar()).
        """
        self._build_file_menu(menubar)
        self._build_edit_menu(menubar)
        self._build_settings_menu(menubar)
        self._build_tools_menu(menubar)
        self._build_help_menu(menubar)
        self._attach_corner_widget(menubar)

    # ------------------------------------------------------------------
    # Private – one method per top-level menu
    # ------------------------------------------------------------------

    def _build_file_menu(self, menubar: QMenuBar) -> None:
        """Builds the File menu with refresh, save, VDF-merge, and exit actions.

        Args:
            menubar: The parent menu bar to add the menu to.
        """
        mw = self.main_window
        file_menu = menubar.addMenu(t('ui.menu.file.root'))

        # Refresh
        refresh_action = QAction(t('ui.menu.file.refresh'), mw)
        refresh_action.triggered.connect(mw.file_actions.refresh_data)
        file_menu.addAction(refresh_action)

        # Save
        save_action = QAction(t('ui.menu.file.save'), mw)
        save_action.triggered.connect(mw.file_actions.force_save)
        file_menu.addAction(save_action)

        # Steam VDF Merge
        vdf_merge_action = QAction(t('ui.menu.file.steam_vdf_merge'), mw)
        vdf_merge_action.triggered.connect(mw.file_actions.show_vdf_merger)
        file_menu.addAction(vdf_merge_action)

        # Remove duplicate collections
        remove_dupes_action = QAction(t('ui.menu.file.remove_duplicates'), mw)
        remove_dupes_action.triggered.connect(mw.file_actions.remove_duplicate_collections)
        file_menu.addAction(remove_dupes_action)

        file_menu.addSeparator()

        # Exit
        exit_action = QAction(t('ui.menu.file.exit'), mw)
        exit_action.triggered.connect(mw.file_actions.exit_application)
        file_menu.addAction(exit_action)

    def _build_edit_menu(self, menubar: QMenuBar) -> None:
        """Builds the Edit menu with bulk-edit and auto-categorize actions.

        Args:
            menubar: The parent menu bar to add the menu to.
        """
        mw = self.main_window
        edit_menu = menubar.addMenu(t('ui.menu.edit.root'))

        # Bulk Edit
        bulk_edit_action = QAction(t('ui.menu.edit.bulk_edit'), mw)
        bulk_edit_action.triggered.connect(mw.bulk_edit_metadata)
        edit_menu.addAction(bulk_edit_action)

        # Auto-Categorize
        auto_cat_action = QAction(t('ui.menu.edit.auto_categorize'), mw)
        auto_cat_action.triggered.connect(mw.auto_categorize)
        edit_menu.addAction(auto_cat_action)

    def _build_settings_menu(self, menubar: QMenuBar) -> None:
        """Builds the Settings menu with settings dialog and metadata restore.

        NOTE: The restore action intentionally uses the 'ui.menu.file.import_json'
        key – this is an existing placeholder in the locale files that the other
        AI kept.  A dedicated key should be added in a future i18n pass.

        Args:
            menubar: The parent menu bar to add the menu to.
        """
        mw = self.main_window
        settings_menu = menubar.addMenu(t('ui.settings.title'))

        # Settings dialog
        settings_action = QAction(t('ui.settings.title'), mw)
        settings_action.triggered.connect(mw.show_settings)
        settings_menu.addAction(settings_action)

        settings_menu.addSeparator()

        # Restore Metadata – uses import_json key as placeholder (see note above)
        restore_action = QAction(t('ui.menu.file.import_json'), mw)
        restore_action.triggered.connect(mw.restore_metadata_changes)
        settings_menu.addAction(restore_action)

    def _build_tools_menu(self, menubar: QMenuBar) -> None:
        """Builds the Tools menu with missing-metadata finder.

        Args:
            menubar: The parent menu bar to add the menu to.
        """
        mw = self.main_window
        tools_menu = menubar.addMenu(t('ui.menu.tools.root'))

        # Find missing metadata
        find_missing_action = QAction(t('ui.menu.tools.missing_meta'), mw)
        find_missing_action.triggered.connect(mw.find_missing_metadata)
        tools_menu.addAction(find_missing_action)

    def _build_help_menu(self, menubar: QMenuBar) -> None:
        """Builds the Help menu with GitHub, donate, and about actions.

        Args:
            menubar: The parent menu bar to add the menu to.
        """
        mw = self.main_window
        help_menu = menubar.addMenu(t('ui.menu.help.root'))

        # GitHub
        github_action = QAction(t('ui.menu.help.github'), mw)
        github_action.triggered.connect(
            lambda: QDesktopServices.openUrl(QUrl("https://github.com/Switch-Bros/SteamLibraryManager"))
        )
        help_menu.addAction(github_action)

        # Donate
        donate_action = QAction(t('ui.menu.help.donate'), mw)
        donate_action.triggered.connect(
            lambda: QDesktopServices.openUrl(QUrl("https://paypal.me/"))
        )
        help_menu.addAction(donate_action)

        help_menu.addSeparator()

        # About
        about_action = QAction(t('ui.menu.help.about'), mw)
        about_action.triggered.connect(mw.show_about)
        help_menu.addAction(about_action)

    def _attach_corner_widget(self, menubar: QMenuBar) -> None:
        """Attaches the user-info label to the top-right corner of the menu bar.

        Args:
            menubar: The menu bar to attach the corner widget to.
        """
        self.user_label.setStyleSheet("padding: 5px 10px;")
        menubar.setCornerWidget(self.user_label, Qt.Corner.TopRightCorner)
