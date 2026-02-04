# src/ui/builders/toolbar_builder.py

"""
Builder for the main application toolbar.

Extracts the toolbar construction and refresh logic that currently lives
in MainWindow._refresh_toolbar(). The toolbar is rebuilt on login/logout
so the builder exposes a single rebuild() method.
"""

from __future__ import annotations
from typing import TYPE_CHECKING

from PyQt6.QtGui import QAction, QIcon
from PyQt6.QtWidgets import QToolBar

from src.config import config
from src.ui.components.ui_helper import UIHelper
from src.utils.i18n import t

if TYPE_CHECKING:
    from src.ui.main_window import MainWindow


class ToolbarBuilder:
    """Constructs and rebuilds the main QToolBar.

    The toolbar content depends on authentication state (login button vs.
    username), so the entire toolbar is cleared and rebuilt whenever that
    state changes.  This mirrors the previous MainWindow._refresh_toolbar()
    behaviour exactly.

    Attributes:
        main_window: Back-reference to the owning MainWindow instance.
    """

    def __init__(self, main_window: 'MainWindow') -> None:
        """Initializes the ToolbarBuilder.

        Args:
            main_window: The MainWindow instance that owns the toolbar.
        """
        self.main_window: 'MainWindow' = main_window

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def build(self, toolbar: QToolBar) -> None:
        """Populates (or re-populates) a QToolBar with current actions.

        Clears the toolbar first so it can be called on every auth-state change
        without duplicating actions.

        Args:
            toolbar: The QToolBar instance to populate.
        """
        toolbar.clear()
        mw = self.main_window

        # --- Always-visible actions ---
        toolbar.addAction(t('ui.menu.file.refresh'), mw.file_actions.refresh_data)
        toolbar.addAction(t('ui.menu.edit.auto_categorize'), mw.auto_categorize)
        toolbar.addSeparator()
        toolbar.addAction(t('ui.settings.title'), mw.show_settings)
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
        """Adds the logged-in user action with icon and tooltip.

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
        """Adds the Steam login button when no user is authenticated.

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
