#
# steam_library_manager/core/appinfo_manager.py
# Manages Steam app metadata modifications and binary appinfo.vdf operations
#
# Copyright © 2025-2026 SwitchBros
# Licensed under the MIT License. See LICENSE for details.
#

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from steam_library_manager.utils.appinfo import AppInfo, IncompatibleVersionError
from steam_library_manager.utils.i18n import t
from steam_library_manager.utils.json_utils import load_json, save_json

logger = logging.getLogger("steamlibmgr.appinfo_manager")

__all__ = ["AppInfoManager", "extract_associations"]


def extract_associations(associations, assoc_type):
    # extract names of given type from VDF associations block
    if not isinstance(associations, dict):
        return []
    return [
        str(entry["name"])
        for entry in associations.values()
        if isinstance(entry, dict) and entry.get("type") == assoc_type and entry.get("name")
    ]


class AppInfoManager:
    """Manages Steam app metadata with VDF write support."""

    def __init__(self, steam_path: Path | None = None):
        from steam_library_manager.config import config

        self.data_dir = config.DATA_DIR
        self.metadata_file = self.data_dir / "custom_metadata.json"

        # tracking dicts
        self.modifications = {}
        self.modified_apps = []

        # dirty flag for VDF write
        self.vdf_dirty = False

        # appinfo.vdf object
        self.appinfo = None
        self.appinfo_path = None

        # steam apps cache
        self.steam_apps = {}

        if steam_path:
            self.appinfo_path = steam_path / "appcache" / "appinfo.vdf"

    def load_appinfo(self, _app_ids=None, _load_all=False):
        # load binary appinfo.vdf and saved modifications
        self.data_dir.mkdir(exist_ok=True)

        # load saved modifications
        self._load_modifications()

        # load binary appinfo.vdf
        if self.appinfo_path and self.appinfo_path.exists():
            try:
                self.appinfo = AppInfo(path=str(self.appinfo_path))
                self.steam_apps = self.appinfo.apps

                count = len(self.appinfo.apps)
                logger.info(t("logs.appinfo.loaded_binary", count=count))

            except IncompatibleVersionError as e:
                logger.info(t("logs.appinfo.incompatible_version", version=hex(e.version)))
            except Exception as e:
                logger.error(t("logs.appinfo.binary_error", error=str(e)))
                import traceback

                traceback.print_exc()

        return self.modifications

    def _load_modifications(self):
        # load custom_metadata.json
        data = load_json(self.metadata_file)
        if not data:
            self.modifications = {}
            self.modified_apps = []
            return

        self.modifications = {}
        self.modified_apps = []

        for app_id_str, mod_data in data.items():
            if isinstance(mod_data, dict):
                # new format with original/modified
                if "original" in mod_data or "modified" in mod_data:
                    self.modifications[app_id_str] = mod_data
                else:
                    # old format: direct metadata
                    self.modifications[app_id_str] = {"original": {}, "modified": mod_data}

                self.modified_apps.append(app_id_str)

        logger.info(t("logs.appinfo.loaded", count=len(self.modifications)))

    def load_modifications_only(self):
        # load only JSON, skip VDF parsing
        self.data_dir.mkdir(exist_ok=True)
        self._load_modifications()
        return self.modifications

    @staticmethod
    def _find_common_section(data):
        # recursively search for 'common' section in VDF data
        if "common" in data:
            return data["common"]

        if "appinfo" in data and "common" in data["appinfo"]:
            return data["appinfo"]["common"]

        # recursive search (limited depth)
        for key, value in data.items():
            if isinstance(value, dict):
                if "common" in value:
                    return value["common"]
                if "appinfo" in value and "common" in value["appinfo"]:
                    return value["appinfo"]["common"]

        return {}

    def get_app_metadata(self, app_id: str) -> dict[str, Any]:
        # get metadata with user modifications applied
        result = {}

        # get from binary appinfo
        if self.appinfo and int(app_id) in self.appinfo.apps:
            app_data = self.appinfo.apps[int(app_id)]
            vdf_data = app_data.get("data", {})

            common = self._find_common_section(vdf_data)

            if common:
                result["name"] = common.get("name", "")
                result["type"] = common.get("type", "")

                # devs & pubs from associations
                devs = extract_associations(common.get("associations", {}), "developer")
                pubs = extract_associations(common.get("associations", {}), "publisher")

                # fallback to direct fields
                if not devs:
                    dev = common.get("developer", "")
                    if dev:
                        devs = [str(dev)]

                if not pubs:
                    pub = common.get("publisher", "")
                    if pub:
                        pubs = [str(pub)]

                result["developer"] = ", ".join(devs) if devs else ""
                result["publisher"] = ", ".join(pubs) if pubs else ""

                # release date
                if "steam_release_date" in common:
                    result["release_date"] = common.get("steam_release_date", "")
                elif "release_date" in common:
                    result["release_date"] = common.get("release_date", "")
                else:
                    result["release_date"] = ""

                # review & metacritic
                if "review_percentage" in common:
                    result["review_percentage"] = common.get("review_percentage", 0)
                if "metacritic_score" in common:
                    result["metacritic_score"] = common.get("metacritic_score", 0)

        # apply modifications
        if app_id in self.modifications:
            modified = self.modifications[app_id].get("modified", {})
            result.update(modified)

        return result

    def set_app_metadata(self, app_id, metadata):
        # set custom metadata and track modification
        try:
            # get original values
            if app_id not in self.modifications:
                original = self.get_app_metadata(app_id)
                self.modifications[app_id] = {"original": original.copy(), "modified": {}}

            # update modified values
            self.modifications[app_id]["modified"].update(metadata)

            # track as modified
            if app_id not in self.modified_apps:
                self.modified_apps.append(app_id)

            # apply to binary appinfo if loaded
            if self.appinfo and int(app_id) in self.appinfo.apps:
                self.appinfo.update_app_metadata(int(app_id), metadata)

            self.vdf_dirty = True
            return True

        except Exception as e:
            logger.error(t("logs.appinfo.set_error", app_id=app_id, error=str(e)))
            return False

    def save_appinfo(self):
        # save modifications to JSON file
        result = save_json(self.metadata_file, self.modifications)
        if result:
            logger.info(t("logs.appinfo.saved_mods", count=len(self.modifications)))
        return result

    def write_to_vdf(self, backup=True):
        # write modifications back to binary appinfo.vdf
        if not self.appinfo:
            logger.info(t("logs.appinfo.not_loaded"))
            return False

        try:
            # create backup
            if backup:
                from steam_library_manager.core.backup_manager import BackupManager

                bm = BackupManager()
                backup_path = bm.create_rolling_backup(self.appinfo_path)
                if backup_path:
                    logger.info(t("logs.appinfo.backup_created", path=backup_path))
                else:
                    logger.error(t("logs.appinfo.backup_failed", error=t("common.unknown")))

            # write using appinfo_v2's method
            success = self.appinfo.write()
            if success:
                self.vdf_dirty = False
                logger.info(t("logs.appinfo.saved_vdf"))
            return success

        except Exception as e:
            logger.error(t("logs.appinfo.write_error", error=str(e)))
            logger.error(t("logs.appinfo.write_error_detail", error=e), exc_info=True)
            return False

    def restore_modifications(self, app_ids=None):
        # restore saved modifications to VDF
        if not app_ids:
            app_ids = list(self.modifications.keys())

        if not app_ids:
            return 0

        self.load_appinfo()

        restored = 0
        for app_id in app_ids:
            if app_id in self.modifications:
                modified = self.modifications[app_id].get("modified", {})
                if modified and self.set_app_metadata(app_id, modified):
                    restored += 1

        if restored > 0:
            self.write_to_vdf()
            logger.info(t("logs.appinfo.restored", count=restored))

        return restored

    def get_all_apps(self):
        # return all parsed apps
        return self.steam_apps

    def get_modification_count(self):
        # return number of modified apps
        return len(self.modifications)

    def clear_all_modifications(self):
        # clear all modifications and save empty state
        count = len(self.modifications)
        self.modifications = {}
        self.modified_apps = []
        self.save_appinfo()
        return count
