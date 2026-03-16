#
# steam_library_manager/ui/actions/profile_actions.py
# Profile management actions (save, load, export, import)
#
# Copyright © 2025-2026 SwitchBros
# Licensed under the MIT License. See LICENSE for details.
#

from __future__ import annotations

import copy
import logging
import time
from typing import TYPE_CHECKING

from PyQt6.QtWidgets import QFileDialog

from steam_library_manager.config import config
from steam_library_manager.core.profile_manager import Profile, ProfileManager
from steam_library_manager.services.filter_service import FilterState
from steam_library_manager.ui.widgets.ui_helper import UIHelper
from steam_library_manager.utils.i18n import t

if TYPE_CHECKING:
    from steam_library_manager.ui.main_window import MainWindow

logger = logging.getLogger("steamlibmgr.profile_actions")

__all__ = ["ProfileActions"]


class ProfileActions:
    """Handles all profile-related UI actions."""

    def __init__(self, main_window: MainWindow) -> None:
        self.mw: MainWindow = main_window
        self.manager: ProfileManager = ProfileManager()

    def save_current_as_profile(self) -> None:
        """Prompts the user for a name and saves the current state as a profile."""
        name, ok = UIHelper.ask_text(
            self.mw,
            title=t("ui.profile.new_title"),
            label=t("ui.profile.new_prompt"),
        )
        if not ok or not name:
            return

        existing = [n for n, _ in self.manager.list_profiles()]
        if name in existing:
            overwrite = UIHelper.confirm(
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
        """Loads a profile after user confirmation."""
        confirmed = UIHelper.confirm(
            self.mw,
            t("ui.profile.load_confirm", name=name),
            title=t("ui.profile.load_confirm_title"),
        )
        if not confirmed:
            return

        try:
            profile = self.manager.load_profile(name)
        except (FileNotFoundError, Exception) as exc:
            UIHelper.show_error(self.mw, t("ui.profile.error_load_failed", error=str(exc)))
            return

        self._apply_profile(profile)
        UIHelper.show_success(self.mw, t("ui.profile.load_success", name=name))

    def show_profile_manager(self) -> None:
        """Opens the profile management dialog."""
        from steam_library_manager.ui.dialogs.profile_dialog import ProfileDialog

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
        """Exports a profile to a user-chosen file path."""
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
            UIHelper.show_error(self.mw, t("ui.profile.error_import_failed", error=str(exc)))

    def _snapshot_current_state(self, name: str) -> Profile:
        """Creates a Profile snapshot from the current application state."""
        collections: tuple[dict, ...] = ()
        parser = self.mw.cloud_storage_parser
        if parser and hasattr(parser, "collections") and parser.collections:
            collections = tuple(copy.deepcopy(parser.collections))

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
        """Applies a loaded profile to the current application state."""
        parser = self.mw.cloud_storage_parser
        if parser and hasattr(parser, "collections"):
            parser.mark_all_managed_as_deleted()
            parser.collections = list(profile.collections)
            parser.modified = True

        config.TAGS_PER_GAME = profile.tags_per_game
        config.IGNORE_COMMON_TAGS = profile.ignore_common_tags
        config.save()

        restored_filter = FilterState(
            enabled_types=profile.filter_enabled_types,
            enabled_platforms=profile.filter_enabled_platforms,
            active_statuses=profile.filter_active_statuses,
        )
        self.mw.filter_service.restore_state(restored_filter)

        self.mw.save_collections()
        self.mw.populate_categories()
