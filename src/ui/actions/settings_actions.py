# src/ui/actions/settings_actions.py

"""
Action handler for Settings operations.

Extracts settings dialog and language change logic from MainWindow.
"""

from __future__ import annotations
from typing import TYPE_CHECKING, Any

from src.ui.settings_dialog import SettingsDialog
from src.config import config
from src.utils.i18n import t, init_i18n

if TYPE_CHECKING:
    from src.ui.main_window import MainWindow

class SettingsActions:
    """Handles settings dialog and configuration changes."""

    def __init__(self, main_window: 'MainWindow') -> None:
        """Initialize SettingsActions.

        Args:
            main_window: The MainWindow instance.
        """
        self.mw: 'MainWindow' = main_window

    def show_settings(self) -> None:
        """Opens the settings dialog and applies changes."""
        dialog = SettingsDialog(self.mw)
        # noinspection PyUnresolvedReferences
        dialog.language_changed.connect(self.on_language_changed_live)

        if dialog.exec():
            settings = dialog.get_settings()
            if settings:
                self.apply_settings(settings)

    def on_language_changed_live(self, new_language: str) -> None:
        """Handles live language change from settings dialog.

        Args:
            new_language: The new language code (e.g., 'en', 'de').
        """
        config.UI_LANGUAGE = new_language
        init_i18n(new_language)
        self._refresh_ui()

    def apply_settings(self, settings: dict[str, Any]) -> None:
        """Applies settings from the settings dialog.

        Args:
            settings: Dictionary containing all settings values.
        """
        # Steam path
        if 'steam_path' in settings and settings['steam_path']:
            config.STEAM_PATH = settings['steam_path']

        # User ID
        if 'user_id' in settings and settings['user_id']:
            config.USER_ID = settings['user_id']

        # UI Language
        if 'ui_language' in settings and settings['ui_language']:
            new_lang = settings['ui_language']
            if new_lang != config.UI_LANGUAGE:
                config.UI_LANGUAGE = new_lang
                init_i18n(new_lang)
                self._refresh_ui()

        # Tags Language
        if 'tags_language' in settings and settings['tags_language']:
            config.TAGS_LANGUAGE = settings['tags_language']

        # SteamGridDB API Key
        if 'steamgriddb_api_key' in settings:
            config.STEAMGRIDDB_API_KEY = settings['steamgriddb_api_key']

        # Save config
        config.save()
        self.mw.set_status(t('ui.settings.applied'))

    def _refresh_ui(self) -> None:
        """Refreshes UI after language change."""
        self.mw.menuBar().clear()
        self.mw.menu_builder.build(self.mw.menuBar())
        self.mw.user_label = self.mw.menu_builder.user_label
        self.mw.refresh_toolbar()
        self.mw.setWindowTitle(t('ui.main_window.title'))
        self.mw.set_status(t('ui.main_window.status_ready'))