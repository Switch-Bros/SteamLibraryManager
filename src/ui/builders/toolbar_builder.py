# src/ui/builders/toolbar_builder.py

"""
Builder for the main application toolbar.

Extracts the toolbar construction and refresh logic.
The toolbar is rebuilt on login/logout so the builder exposes a build() method.
"""

from __future__ import annotations
from typing import TYPE_CHECKING

from PyQt6.QtGui import QAction, QIcon
from PyQt6.QtWidgets import QToolBar, QWidget, QSizePolicy

from src.config import config
from src.ui.components.ui_helper import UIHelper
from src.utils.i18n import t

if TYPE_CHECKING:
    from src.ui.main_window import MainWindow


class ToolbarBuilder:
    """
    Constructs and rebuilds the main QToolBar.

    The toolbar content depends on authentication state (login button vs.
    username), so the entire toolbar is cleared and rebuilt whenever that
    state changes.

    Attributes:
        main_window: Back-reference to the owning MainWindow instance.
    """

    def __init__(self, main_window: 'MainWindow') -> None:
        """
        Initializes the ToolbarBuilder.

        Args:
            main_window: The MainWindow instance that owns the toolbar.
        """
        self.main_window: 'MainWindow' = main_window

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def build(self, toolbar: QToolBar) -> None:
        """
        Populates (or re-populates) a QToolBar with current actions.

        Clears the toolbar first so it can be called on every auth-state change
        without duplicating actions.

        Args:
            toolbar: The QToolBar instance to populate.
        """
        toolbar.clear()
        toolbar.setMovable(False)
        toolbar.setFloatable(False)

        mw = self.main_window

        # --- Always-visible actions ---

        # Refresh
        refresh_action = QAction("⟳", mw)
        refresh_action.setToolTip(t('ui.menu.file.refresh'))
        refresh_action.triggered.connect(mw.file_actions.refresh_data)
        toolbar.addAction(refresh_action)

        # Save
        save_action = QAction("💾", mw)
        save_action.setToolTip(t('ui.menu.file.save'))
        save_action.triggered.connect(mw.file_actions.force_save)
        toolbar.addAction(save_action)

        toolbar.addSeparator()

        # --- Edit Actions (Fixed: redirects to edit_actions) ---

        # Auto Categorize
        auto_cat_action = QAction("⚡", mw)
        auto_cat_action.setToolTip(t('ui.menu.edit.auto_categorize'))
        # FIX: Was mw.auto_categorize, now mw.edit_actions.auto_categorize
        auto_cat_action.triggered.connect(mw.edit_actions.auto_categorize)
        toolbar.addAction(auto_cat_action)

        # Bulk Edit
        bulk_edit_action = QAction("✏️", mw)
        bulk_edit_action.setToolTip(t('ui.menu.edit.bulk_edit'))
        # FIX: Was mw.bulk_edit_metadata, now mw.edit_actions.bulk_edit_metadata
        bulk_edit_action.triggered.connect(mw.edit_actions.bulk_edit_metadata)
        toolbar.addAction(bulk_edit_action)

        toolbar.addSeparator()

        # --- Tools ---

        # Missing Metadata
        missing_meta_action = QAction("🔍", mw)
        missing_meta_action.setToolTip(t('ui.menu.tools.missing_meta'))
        missing_meta_action.triggered.connect(mw.find_missing_metadata)
        toolbar.addAction(missing_meta_action)

        # --- Spacer & Settings ---
        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        toolbar.addWidget(spacer)

        settings_action = QAction("⚙️", mw)
        settings_action.setToolTip(t('ui.settings.title'))
        settings_action.triggered.connect(mw.show_settings)
        toolbar.addAction(settings_action)

        toolbar.addSeparator()

        # --- Auth-dependent section ---
        if mw.steam_username:
            self._add_logged_in_action(toolbar)
        else:
            self._add_login_action(toolbar)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _add_logged_in_action(self, toolbar: QToolBar) -> None:
        """
        Adds the logged-in user action with icon and tooltip.

        Args:
            toolbar: The toolbar to add the action to.
        """
        mw = self.main_window
        user_action = QAction(mw.steam_username, mw)

        # Localized tooltip
        tooltip: str = t('ui.login.logged_in_as', user=mw.steam_username)
        user_action.setToolTip(tooltip)

        # Show tooltip text in an info popup when clicked
        user_action.triggered.connect(
            lambda: UIHelper.show_success(mw, tooltip, "Steam")
        )

        # Steam login icon (shared with the login button)
        icon_path = config.ICONS_DIR / 'steam_login.png'
        if icon_path.exists():
            user_action.setIcon(QIcon(str(icon_path)))

        toolbar.addAction(user_action)

    def _add_login_action(self, toolbar: QToolBar) -> None:
        """
        Adds the Steam login button when no user is authenticated.

        Args:
            toolbar: The toolbar to add the action to.
        """
        mw = self.main_window
        login_action = QAction(t('ui.login.button'), mw)

        icon_path = config.ICONS_DIR / 'steam_login.png'
        if icon_path.exists():
            login_action.setIcon(QIcon(str(icon_path)))

        # noinspection PyProtectedMember
        login_action.triggered.connect(mw._start_steam_login)
        toolbar.addAction(login_action)