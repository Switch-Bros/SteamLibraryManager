# src/ui/builders/toolbar_builder.py

"""
Builder for the main application toolbar.

Extracts the toolbar construction and refresh logic.
The toolbar is rebuilt on login/logout so the builder exposes a build() method.
Handles strict I18N compliance by pulling both text and icons/emojis from locales.
"""

from __future__ import annotations
from typing import TYPE_CHECKING

from PyQt6.QtGui import QAction, QIcon
from PyQt6.QtWidgets import QToolBar, QWidget, QSizePolicy
from PyQt6.QtCore import Qt

from src.config import config
from src.ui.widgets.ui_helper import UIHelper
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
        without duplicating actions. Enforces 'Icon + Text' style by explicitly
        setting the tool button style.

        Args:
            toolbar: The QToolBar instance to populate.
        """
        toolbar.clear()
        toolbar.setMovable(False)
        toolbar.setFloatable(False)
        # Ensure text is shown alongside icons/emojis
        toolbar.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)

        mw = self.main_window

        # --- Always-visible actions ---

        # Refresh: [Emoji] [Text]
        refresh_text = f"{t('emoji.refresh')} {t('ui.menu.file.refresh')}"
        refresh_action = QAction(refresh_text, mw)
        refresh_action.setToolTip(t('ui.menu.file.refresh'))
        refresh_action.triggered.connect(mw.file_actions.refresh_data)
        toolbar.addAction(refresh_action)

        # Save: [Emoji] [Text]
        save_text = f"{t('emoji.save')} {t('ui.menu.file.save')}"
        save_action = QAction(save_text, mw)
        save_action.setToolTip(t('ui.menu.file.save'))
        save_action.triggered.connect(mw.file_actions.force_save)
        toolbar.addAction(save_action)

        toolbar.addSeparator()

        # --- Edit Actions ---

        # Auto Categorize: [Emoji] [Text]
        auto_text = f"{t('emoji.blitz')} {t('ui.menu.edit.auto_categorize')}"
        auto_cat_action = QAction(auto_text, mw)
        auto_cat_action.setToolTip(t('ui.menu.edit.auto_categorize'))
        auto_cat_action.triggered.connect(mw.edit_actions.auto_categorize)
        toolbar.addAction(auto_cat_action)

        # Bulk Edit: [Emoji] [Text]
        edit_text = f"{t('emoji.edit')} {t('ui.menu.edit.bulk_edit')}"
        bulk_edit_action = QAction(edit_text, mw)
        bulk_edit_action.setToolTip(t('ui.menu.edit.bulk_edit'))
        bulk_edit_action.triggered.connect(mw.edit_actions.bulk_edit_metadata)
        toolbar.addAction(bulk_edit_action)

        toolbar.addSeparator()

        # --- Tools ---

        # Missing Metadata: [Emoji] [Text] (Using 'search' emoji as placeholder)
        search_text = f"{t('emoji.search')} {t('ui.menu.tools.missing_meta')}"
        missing_meta_action = QAction(search_text, mw)
        missing_meta_action.setToolTip(t('ui.menu.tools.missing_meta'))
        missing_meta_action.triggered.connect(mw.find_missing_metadata)
        toolbar.addAction(missing_meta_action)

        # --- Spacer & Settings ---
        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        toolbar.addWidget(spacer)

        # Settings: [Emoji] [Text]
        settings_text = f"{t('emoji.settings')} {t('ui.settings.title')}"
        settings_action = QAction(settings_text, mw)
        settings_action.setToolTip(t('ui.settings.title'))
        settings_action.triggered.connect(mw.settings_actions.show_settings)
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

        # Display: [User Emoji] [Username]
        action_text = f"{t('emoji.user')} {mw.steam_username}"
        user_action = QAction(action_text, mw)

        # Localized tooltip using t()
        tooltip_text = t('ui.login.logged_in_as', user=mw.steam_username)
        user_action.setToolTip(tooltip_text)

        # Show info on click
        user_action.triggered.connect(
            lambda: UIHelper.show_success(mw, tooltip_text, "Steam")
        )

        # Steam login icon (if available, set as QIcon alongside text)
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

        # Display: [Login Emoji] [Login Text]
        action_text = f"{t('emoji.login')} {t('ui.login.button')}"
        login_action = QAction(action_text, mw)
        login_action.setToolTip(t('ui.login.button'))

        icon_path = config.ICONS_DIR / 'steam_login.png'
        if icon_path.exists():
            login_action.setIcon(QIcon(str(icon_path)))

        # Use SteamActions instead of MainWindow method
        login_action.triggered.connect(mw.steam_actions.start_steam_login)
        toolbar.addAction(login_action)