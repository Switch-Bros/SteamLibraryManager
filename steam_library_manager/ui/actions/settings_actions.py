#
# steam_library_manager/ui/actions/settings_actions.py
# Settings dialog and configuration change handling
#
# Copyright © 2025-2026 SwitchBros
# Licensed under the MIT License. See LICENSE for details.
#

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

from steam_library_manager.config import config
from steam_library_manager.ui.dialogs.settings_dialog import SettingsDialog
from steam_library_manager.utils.i18n import t, init_i18n
from steam_library_manager.version import __app_name__

if TYPE_CHECKING:
    from steam_library_manager.ui.main_window import MainWindow

__all__ = ["SettingsActions"]


class SettingsActions:
    """Handles settings dialog and configuration changes."""

    def __init__(self, main_window: "MainWindow") -> None:
        self.mw: "MainWindow" = main_window

    def show_settings(self) -> None:
        """Opens the settings dialog and applies changes on save.

        Tracks the last persisted language so unsaved live-preview
        changes are reverted when the dialog is closed without saving.
        """
        self._last_persisted_language = config.UI_LANGUAGE
        dialog = SettingsDialog(self.mw)
        dialog.language_changed.connect(self.on_language_changed_live)
        dialog.settings_saved.connect(self.apply_settings)
        dialog.exec()
        if config.UI_LANGUAGE != self._last_persisted_language:
            config.UI_LANGUAGE = self._last_persisted_language
            init_i18n(self._last_persisted_language)
            self._refresh_ui()

    def on_language_changed_live(self, new_language: str) -> None:
        """Handles live language change from settings dialog."""
        config.UI_LANGUAGE = new_language
        init_i18n(new_language)
        self._refresh_ui()

    def apply_settings(self, settings: dict[str, Any]) -> None:
        """Applies settings from the settings dialog."""
        if "steam_path" in settings and settings["steam_path"]:
            config.STEAM_PATH = Path(settings["steam_path"])

        if "ui_language" in settings and settings["ui_language"]:
            new_lang = settings["ui_language"]
            if new_lang != config.UI_LANGUAGE:
                config.UI_LANGUAGE = new_lang
                init_i18n(new_lang)
                self._refresh_ui()

        if "tags_language" in settings and settings["tags_language"]:
            config.TAGS_LANGUAGE = settings["tags_language"]

        if "tags_per_game" in settings:
            config.TAGS_PER_GAME = settings["tags_per_game"]
        if "ignore_common_tags" in settings:
            config.IGNORE_COMMON_TAGS = settings["ignore_common_tags"]

        if "max_backups" in settings:
            config.MAX_BACKUPS = settings["max_backups"]

        if "steam_libraries" in settings:
            config.STEAM_LIBRARIES = settings["steam_libraries"]

        if "steam_api_key" in settings:
            config.STEAM_API_KEY = settings["steam_api_key"] or None
        if "steamgriddb_api_key" in settings:
            config.STEAMGRIDDB_API_KEY = settings["steamgriddb_api_key"] or None

        config.save()
        self._last_persisted_language = config.UI_LANGUAGE
        self.mw.set_status(t("settings.applied"))

    def _refresh_ui(self) -> None:
        """Refreshes UI after language change."""
        self.mw.menuBar().clear()
        self.mw.menu_builder.build(self.mw.menuBar())
        self.mw.user_label = self.mw.menu_builder.user_label
        self.mw.refresh_toolbar()
        self.mw.setWindowTitle(__app_name__)
        self.mw.set_status(t("ui.main_window.status_ready"))
