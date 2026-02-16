# src/ui/actions/profile_actions.py

"""Action handler for profile management operations.

Bridges the UI layer (dialogs, menus) with the core ProfileManager.
Handles snapshot creation, profile application, export, and import.
"""

from __future__ import annotations

import copy
import logging
import time
from typing import TYPE_CHECKING

from PyQt6.QtWidgets import QFileDialog

from src.config import config
from src.core.profile_manager import Profile, ProfileManager
from src.services.filter_service import FilterState
from src.ui.utils.dialog_helpers import ask_confirmation, ask_text_input, show_error
from src.ui.widgets.ui_helper import UIHelper
from src.utils.i18n import t

if TYPE_CHECKING:
    from src.ui.main_window import MainWindow

logger = logging.getLogger("steamlibmgr.profile_actions")

__all__ = ["ProfileActions"]


class ProfileActions:
    """Handles all profile-related UI actions.

    Owns a ProfileManager and provides methods for saving, loading,
    exporting, importing, and managing profiles via dialog interactions.

    Attributes:
        mw: Back-reference to the owning MainWindow instance.
        manager: The underlying ProfileManager for file operations.
    """

    def __init__(self, main_window: MainWindow) -> None:
        """Initializes the ProfileActions handler.

        Args:
            main_window: The MainWindow instance that owns these actions.
        """
        self.mw: MainWindow = main_window
        self.manager: ProfileManager = ProfileManager()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def save_current_as_profile(self) -> None:
        """Prompts the user for a name and saves the current state as a profile."""
        name = ask_text_input(
            self.mw,
            title=t("ui.profile.new_title"),
            label=t("ui.profile.new_prompt"),
        )
        if not name:
            return

        # Check for existing profile with same name
        existing = [n for n, _ in self.manager.list_profiles()]
        if name in existing:
            overwrite = ask_confirmation(
                self.mw,
                t("ui.profile.error_duplicate_name", name=name),
                title=t("ui.profile.new_title"),
            )
            if not overwrite:
                return

        profile = self._snapshot_current_state(name)
        self.manager.save_profile(profile)
        UIHelper.show_success(self.mw, t("ui.profile.save_success", name=name))

    def load_profile(self, name: str) -> None:
        """Loads a profile after user confirmation.

        Args:
            name: The profile name to load.
        """
        confirmed = ask_confirmation(
            self.mw,
            t("ui.profile.load_confirm", name=name),
            title=t("ui.profile.load_confirm_title"),
        )
        if not confirmed:
            return

        try:
            profile = self.manager.load_profile(name)
        except (FileNotFoundError, Exception) as exc:
            show_error(self.mw, t("ui.profile.error_load_failed", error=str(exc)))
            return

        self._apply_profile(profile)
        UIHelper.show_success(self.mw, t("ui.profile.load_success", name=name))

    def show_profile_manager(self) -> None:
        """Opens the profile management dialog."""
        from src.ui.dialogs.profile_dialog import ProfileDialog

        dialog = ProfileDialog(self.manager, parent=self.mw)
        result = dialog.exec()

        if result == ProfileDialog.DialogCode.Accepted:
            action = dialog.action
            selected = dialog.selected_name

            if action == "save" and selected:
                profile = self._snapshot_current_state(selected)
                self.manager.save_profile(profile)
                UIHelper.show_success(self.mw, t("ui.profile.save_success", name=selected))

            elif action == "load" and selected:
                self.load_profile(selected)

    def export_profile(self, name: str) -> None:
        """Exports a profile to a user-chosen file path.

        Args:
            name: The profile name to export.
        """
        file_path, _ = QFileDialog.getSaveFileName(
            self.mw,
            t("ui.profile.export_title"),
            f"{name}.json",
            t("ui.profile.import_filter"),
        )
        if not file_path:
            return

        from pathlib import Path

        success = self.manager.export_profile(name, Path(file_path))
        if success:
            UIHelper.show_success(self.mw, t("ui.profile.export_success"))

    def import_profile(self) -> None:
        """Imports a profile from a user-chosen file."""
        file_path, _ = QFileDialog.getOpenFileName(
            self.mw,
            t("ui.profile.import_title"),
            "",
            t("ui.profile.import_filter"),
        )
        if not file_path:
            return

        from pathlib import Path

        try:
            profile = self.manager.import_profile(Path(file_path))
            UIHelper.show_success(self.mw, t("ui.profile.import_success", name=profile.name))
        except (FileNotFoundError, KeyError, Exception) as exc:
            show_error(self.mw, t("ui.profile.error_import_failed", error=str(exc)))

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _snapshot_current_state(self, name: str) -> Profile:
        """Creates a Profile snapshot from the current application state.

        Args:
            name: The name for the new profile.

        Returns:
            A frozen Profile capturing the current collections, filters,
            AutoCat settings, and view mode.
        """
        # Collections from cloud storage parser
        collections: tuple[dict, ...] = ()
        parser = self.mw.cloud_storage_parser
        if parser and hasattr(parser, "collections") and parser.collections:
            collections = tuple(copy.deepcopy(parser.collections))

        # Filter state
        filter_state = self.mw.filter_service.state

        return Profile(
            name=name,
            collections=collections,
            tags_per_game=config.TAGS_PER_GAME,
            ignore_common_tags=config.IGNORE_COMMON_TAGS,
            filter_enabled_types=filter_state.enabled_types,
            filter_enabled_platforms=filter_state.enabled_platforms,
            filter_active_statuses=filter_state.active_statuses,
            sort_key="name",
            created_at=time.time(),
        )

    def _apply_profile(self, profile: Profile) -> None:
        """Applies a loaded profile to the current application state.

        Restores collections, config settings, filter state, and refreshes
        the UI. Triggers a save (which creates an automatic backup).

        Args:
            profile: The profile to apply.
        """
        # 1. Restore collections
        parser = self.mw.cloud_storage_parser
        if parser and hasattr(parser, "collections"):
            parser.collections = list(profile.collections)
            parser.modified = True

        # 2. Restore AutoCat config
        config.TAGS_PER_GAME = profile.tags_per_game
        config.IGNORE_COMMON_TAGS = profile.ignore_common_tags
        config.save()

        # 3. Restore filter state
        restored_filter = FilterState(
            enabled_types=profile.filter_enabled_types,
            enabled_platforms=profile.filter_enabled_platforms,
            active_statuses=profile.filter_active_statuses,
        )
        self.mw.filter_service.restore_state(restored_filter)

        # 4. Persist and refresh UI
        self.mw.save_collections()
        self.mw.populate_categories()
