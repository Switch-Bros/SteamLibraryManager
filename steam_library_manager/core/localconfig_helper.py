#
# steam_library_manager/core/localconfig_helper.py
# Minimal localconfig.vdf parser for hidden status and expand/collapse state
#
# Copyright © 2025-2026 SwitchBros
# Licensed under the MIT License. See LICENSE for details.
#

from __future__ import annotations


import logging
import vdf
from pathlib import Path

from steam_library_manager.utils.i18n import t

logger = logging.getLogger("steamlibmgr.localconfig")

__all__ = ["LocalConfigHelper"]


class LocalConfigHelper:
    """Minimal helper for localconfig.vdf operations."""

    def __init__(self, config_path: str):
        self.config_path = Path(config_path)
        self.data: dict = {}
        self.apps: dict = {}
        self.modified = False

    def load(self) -> bool:
        """Load and parse localconfig.vdf."""
        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                self.data = vdf.load(f)

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
        """Write changes back to localconfig.vdf."""
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

    # Hidden status

    def get_hidden_apps(self) -> list[str]:
        """App IDs marked as hidden in the Steam client."""
        hidden = []
        for app_id, app_data in self.apps.items():
            if app_data.get("hidden", "0") == "1":
                hidden.append(app_id)
        return hidden

    def set_app_hidden(self, app_id: str, hidden: bool):
        app_id = str(app_id)

        if app_id not in self.apps:
            self.apps[app_id] = {}

        self.apps[app_id]["hidden"] = "1" if hidden else "0"
        self.modified = True

    # Expanded/collapsed state

    def get_expanded_state(self, category_id: str) -> bool:
        """Whether a category is expanded (default: True)."""
        if category_id not in self.apps:
            return True  # Default: expanded

        cloud_state = self.apps[category_id].get("CloudLocalAppState", {})
        expanded = cloud_state.get("Expanded", "1")
        return expanded == "1"

    def set_expanded_state(self, category_id: str, expanded: bool):
        if category_id not in self.apps:
            self.apps[category_id] = {}

        if "CloudLocalAppState" not in self.apps[category_id]:
            self.apps[category_id]["CloudLocalAppState"] = {}

        self.apps[category_id]["CloudLocalAppState"]["Expanded"] = "1" if expanded else "0"
        self.modified = True

    def get_all_expanded_states(self) -> dict[str, bool]:
        """Expanded state for all categories that have one."""
        states = {}
        for app_id, app_data in self.apps.items():
            cloud_state = app_data.get("CloudLocalAppState", {})
            if "Expanded" in cloud_state:
                expanded = cloud_state.get("Expanded", "1")
                states[app_id] = expanded == "1"
        return states

    def get_all_app_ids(self) -> list[str]:
        """All app IDs in the localconfig Apps section."""
        return list(self.apps.keys())

    # Cleanup

    def remove_app(self, app_id: str) -> bool:
        """Remove an app entry (for ghost entry cleanup)."""
        app_id = str(app_id)

        if app_id in self.apps:
            del self.apps[app_id]
            self.modified = True
            return True

        return False
