#
# steam_library_manager/ui/actions/profile_actions.py
# UI action handlers for profile switching and management
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
    """UI-facing profile operations -- save, load, export, import."""

    def __init__(self, mw: MainWindow):
        self.mw = mw
        self.manager = ProfileManager()

    # -- public API --

    def save_current_as_profile(self):
        # ask for name, snapshot state, persist
        name, ok = UIHelper.ask_text(
            self.mw,
            title=t("ui.profile.new_title"),
            label=t("ui.profile.new_prompt"),
        )
        if not ok or not name:
            return

        exist = [n for n, _ in self.manager.list_profiles()]
        if name in exist:
            ow = UIHelper.confirm(
                self.mw,
                t("ui.profile.error_duplicate_name", name=name),
                title=t("ui.profile.new_title"),
            )
            if not ow:
                return

        self.manager.save_profile(self._snap(name))
        UIHelper.show_success(self.mw, t("ui.profile.save_success", name=name))

    def load_profile(self, name):
        # confirm, then restore profile
        if not UIHelper.confirm(
            self.mw,
            t("ui.profile.load_confirm", name=name),
            title=t("ui.profile.load_confirm_title"),
        ):
            return

        try:
            p = self.manager.load_profile(name)
        except (FileNotFoundError, Exception) as exc:
            UIHelper.show_error(self.mw, t("ui.profile.error_load_failed", error=str(exc)))
            return

        self._apply(p)
        UIHelper.show_success(self.mw, t("ui.profile.load_success", name=name))

    def show_profile_manager(self):
        # open profile management dialog
        from steam_library_manager.ui.dialogs.profile_dialog import ProfileDialog

        dlg = ProfileDialog(self.manager, parent=self.mw)
        if dlg.exec() != ProfileDialog.DialogCode.Accepted:
            return

        act = dlg.action
        sel = dlg.selected_name

        if act == "save" and sel:
            self.manager.save_profile(self._snap(sel))
            UIHelper.show_success(self.mw, t("ui.profile.save_success", name=sel))
        elif act == "load" and sel:
            self.load_profile(sel)

    def export_profile(self, name):
        # export profile to JSON
        fp, _ = QFileDialog.getSaveFileName(
            self.mw,
            t("ui.profile.export_title"),
            "%s.json" % name,
            t("ui.profile.import_filter"),
        )
        if not fp:
            return

        from pathlib import Path

        if self.manager.export_profile(name, Path(fp)):
            UIHelper.show_success(self.mw, t("ui.profile.export_success"))

    def import_profile(self):
        # import profile from JSON
        fp, _ = QFileDialog.getOpenFileName(
            self.mw,
            t("ui.profile.import_title"),
            "",
            t("ui.profile.import_filter"),
        )
        if not fp:
            return

        from pathlib import Path

        try:
            p = self.manager.import_profile(Path(fp))
            UIHelper.show_success(self.mw, t("ui.profile.import_success", name=p.name))
        except (FileNotFoundError, KeyError, Exception) as exc:
            UIHelper.show_error(self.mw, t("ui.profile.error_import_failed", error=str(exc)))

    # -- internals --

    def _snap(self, name):
        # capture collections, filters, autocat config
        cols = ()
        par = self.mw.cloud_storage_parser
        if par and hasattr(par, "collections") and par.collections:
            # deep copy so mutations don't corrupt snapshot
            cols = tuple(copy.deepcopy(par.collections))

        fs = self.mw.filter_service.state
        return Profile(
            name=name,
            collections=cols,
            tags_per_game=config.TAGS_PER_GAME,
            ignore_common_tags=config.IGNORE_COMMON_TAGS,
            filter_enabled_types=fs.enabled_types,
            filter_enabled_platforms=fs.enabled_platforms,
            filter_active_statuses=fs.active_statuses,
            sort_key="name",
            created_at=time.time(),
        )

    def _apply(self, p):
        # restore profile state into app
        par = self.mw.cloud_storage_parser

        # wipe existing managed collections
        if par and hasattr(par, "collections"):
            par.mark_all_managed_as_deleted()
            par.collections = list(p.collections)
            par.modified = True

        # autocat settings
        config.TAGS_PER_GAME = p.tags_per_game
        config.IGNORE_COMMON_TAGS = p.ignore_common_tags
        config.save()

        # filters
        self.mw.filter_service.restore_state(
            FilterState(
                enabled_types=p.filter_enabled_types,
                enabled_platforms=p.filter_enabled_platforms,
                active_statuses=p.filter_active_statuses,
            )
        )

        # flush to disk and repaint
        self.mw.save_collections()
        self.mw.populate_categories()
