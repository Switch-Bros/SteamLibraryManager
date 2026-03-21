#
# steam_library_manager/core/localconfig_helper.py
# Reads and writes Steam localconfig.vdf for category and collection data
#
# Copyright (c) 2025-2026 SwitchBros
# Licensed under the MIT License. See LICENSE for details.
#
# TODO: refactor this mess

from __future__ import annotations

import logging
import vdf
from pathlib import Path

from steam_library_manager.utils.i18n import t

logger = logging.getLogger("steamlibmgr.localconfig")

__all__ = ["LocalConfigHelper"]


class LocalConfigHelper:
    """Minimal helper for localconfig.vdf."""

    def __init__(self, config_path):
        # setup paths
        self.config_path = Path(config_path)
        self.data = {}
        self.apps = {}
        self.modified = False

    def load(self):
        # parse localconfig.vdf
        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                self.data = vdf.load(f)

            # navigate to Apps section - boring vdf stuff
            steam_section = (
                self.data.get("UserLocalConfigStore", {}).get("Software", {}).get("Valve", {}).get("Steam", {})
            )

            self.apps = steam_section.get("Apps", {})
            return True

        except FileNotFoundError:
            logger.error(t("logs.localconfig.not_found", path=self.config_path))
            return False
        except Exception as e:
            logger.error(t("logs.localconfig.load_error", error=e))
            return False

    def save(self) -> bool:
        # write back to localconfig.vdf
        if not self.modified:
            return True

        try:
            with open(self.config_path, "w", encoding="utf-8") as f:
                vdf.dump(self.data, f, pretty=True)
            self.modified = False
            return True

        except OSError as e:
            logger.error(t("logs.localconfig.save_error", error=e))
            return False

    # hidden apps stuff

    def get_hidden_apps(self):
        # collect hidden app IDs (ugh, stored as "1"/"0" strings)
        out = []
        for aid, ad in self.apps.items():
            if ad.get("hidden", "0") == "1":
                out.append(aid)
        return out

    def set_app_hidden(self, app_id: str, hidden: bool):
        # set hidden flag for app
        aid = str(app_id)

        if aid not in self.apps:
            self.apps[aid] = {}

        self.apps[aid]["hidden"] = "1" if hidden else "0"
        self.modified = True

    # expand/collapse state

    def get_expanded_state(self, category_id):
        # check if category is expanded in UI
        if category_id not in self.apps:
            return True  # default expanded

        cs = self.apps[category_id].get("CloudLocalAppState", {})
        return cs.get("Expanded", "1") == "1"

    def set_expanded_state(self, category_id: str, expanded: bool):
        # set expanded state
        if category_id not in self.apps:
            self.apps[category_id] = {}

        if "CloudLocalAppState" not in self.apps[category_id]:
            self.apps[category_id]["CloudLocalAppState"] = {}

        self.apps[category_id]["CloudLocalAppState"]["Expanded"] = "1" if expanded else "0"
        self.modified = True

    def get_all_expanded_states(self):
        # map all categories to expanded state
        out = {}
        for aid, ad in self.apps.items():
            cs = ad.get("CloudLocalAppState", {})
            if "Expanded" in cs:
                out[aid] = cs.get("Expanded", "1") == "1"
        return out

    # all app IDs

    def get_all_app_ids(self) -> list[str]:
        return list(self.apps.keys())

    # cleanup

    def remove_app(self, app_id: str) -> bool:
        # delete ghost entry
        aid = str(app_id)

        if aid in self.apps:
            del self.apps[aid]
            self.modified = True
            return True

        return False
