#
# steam_library_manager/core/cloud_storage_parser.py
# Steam cloud storage collection parser for cloud-storage-namespace-1.json
#
# Copyright (c) 2025-2026 SwitchBros
# Licensed under the MIT License. See LICENSE for details.
#

from __future__ import annotations

import json
import logging
import os
import time
from pathlib import Path

from steam_library_manager.core.backup_manager import BackupManager
from steam_library_manager.utils.i18n import t

logger = logging.getLogger("steamlibmgr.cloud_parser")

__all__ = ["CloudStorageParser"]


class CloudStorageParser:
    """Parser for Steam cloud-storage-namespace-1.json"""

    @staticmethod
    def _get_virtual_categories():
        # virtual categories that should never be written to cloud
        return {
            t("categories.uncategorized"),
            t("categories.all_games"),
            t("categories.soundtracks"),
            t("categories.tools"),
            t("categories.software"),
            t("categories.videos"),
        }

    @staticmethod
    def _get_special_collection_ids():
        # map display names to Steam internal IDs
        # TODO v1.2: use only collection IDs, remove hardcoded name matching
        mapping = {
            "favorite": "favorite",
            "hidden": "hidden",
            "Favorites": "favorite",
            "Hidden": "hidden",
            "Favoriten": "favorite",
            "Versteckt": "hidden",
        }
        mapping[t("categories.favorites")] = "favorite"
        mapping[t("categories.hidden")] = "hidden"
        return mapping

    def __init__(self, steam_path, user_id):
        # init parser
        self.steam_path = steam_path
        self.user_id = user_id
        self.cloud_storage_path = os.path.join(
            steam_path, "userdata", user_id, "config", "cloudstorage", "cloud-storage-namespace-1.json"
        )
        self.data = []
        self.collections = []
        self.modified = False
        self.had_conflict = False
        self._file_mtime = 0.0
        self._deleted_keys = set()

    def load(self):
        # load collections from cloud storage
        try:
            if not os.path.exists(self.cloud_storage_path):
                return False

            with open(self.cloud_storage_path, "r", encoding="utf-8") as f:
                self.data = json.load(f)

            if not isinstance(self.data, list):
                logger.error(t("logs.parser.not_a_list"))
                return False

            self._file_mtime = os.path.getmtime(self.cloud_storage_path)

            self.collections = []
            for item in self.data:
                if len(item) == 2 and isinstance(item[1], dict):
                    key = item[1].get("key", "")
                    if key.startswith("user-collections."):
                        val_str = item[1].get("value", "{}")
                        if val_str and val_str != "{}":
                            try:
                                col_data = json.loads(val_str)
                                self.collections.append(col_data)
                            except json.JSONDecodeError:
                                logger.warning(t("logs.parser.parse_failed", key=key))

            return True

        except FileNotFoundError:
            logger.error(t("logs.parser.cloud_file_not_found", path=self.cloud_storage_path))
            return False
        except Exception as e:
            logger.error(t("logs.parser.load_error", error=e))
            return False

    def has_external_changes(self):
        # check if file changed since last load
        if not self._file_mtime or not os.path.exists(self.cloud_storage_path):
            return False
        return os.path.getmtime(self.cloud_storage_path) != self._file_mtime

    def mark_all_managed_as_deleted(self):
        # mark all collections for deletion (used by profile restore)
        for col in self.collections:
            cid = col.get("id", "")
            if cid:
                self._deleted_keys.add("user-collections.%s" % cid)

    def save(self):
        # save with delta-merge (never overwrite whole file)
        try:
            self.had_conflict = self.has_external_changes()
            if self.had_conflict:
                logger.warning(t("logs.parser.external_change_detected"))

            # build set of keys we manage
            managed_keys = set()
            for col in self.collections:
                cid = col.get("id", "")
                if cid:
                    managed_keys.add("user-collections.%s" % cid)

            # remove only managed + deleted keys, preserve everything else
            preserved = []
            preserved_count = 0

            for item in self.data:
                if len(item) == 2 and isinstance(item[1], dict):
                    key = item[1].get("key", "")
                    if key.startswith("user-collections."):
                        if key in managed_keys or key in self._deleted_keys:
                            continue  # we'll rewrite these
                        else:
                            preserved_count += 1
                            preserved.append(item)
                            continue
                preserved.append(item)

            self.data = preserved

            if preserved_count > 0 or self._deleted_keys:
                logger.info(
                    t(
                        "logs.parser.delta_merge_stats",
                        managed=len(managed_keys),
                        deleted=len(self._deleted_keys),
                        preserved=preserved_count,
                    )
                )

            # sanitize: 'added' must be list, not int
            for col in self.collections:
                raw = col.get("added", col.get("apps"))
                if not isinstance(raw, list):
                    col["added"] = []
                    col.setdefault("apps", [])

            # add our collections
            ts = int(time.time())
            for col in self.collections:
                cid = col.get("id", "")
                cname = col.get("name", "")

                # skip virtual categories
                if cname in self._get_virtual_categories():
                    continue

                # skip empty special collections (favorites/hidden)
                added_apps = self._get_collection_apps(col)
                specials = self._get_special_collection_ids()
                if cname in specials and not added_apps:
                    continue

                # use correct Steam ID for specials
                if cname in specials:
                    sid = specials[cname]
                    cid = sid
                    col["id"] = sid
                    key = "user-collections.%s" % sid
                elif not cid.startswith("from-tag-") and not cid.startswith("uc-"):
                    cid = "from-tag-%s" % cname
                    col["id"] = cid
                    key = "user-collections.%s" % cid
                else:
                    key = "user-collections.%s" % cid

                # build value JSON
                val_data = {
                    "id": cid,
                    "name": cname,
                    "added": added_apps,
                    "removed": col.get("removed", []),
                }

                if "filterSpec" in col:
                    val_data["filterSpec"] = col["filterSpec"]

                val_str = json.dumps(val_data, separators=(",", ":"))

                item = [
                    key,
                    {"key": key, "timestamp": ts, "value": val_str, "version": str(int(time.time() % 10000))},
                ]

                self.data.append(item)

            # size check safety net
            new_json = json.dumps(self.data, indent=2, ensure_ascii=False)
            cloud_path = Path(self.cloud_storage_path)
            if cloud_path.exists():
                old_size = cloud_path.stat().st_size
                new_size = len(new_json.encode("utf-8"))
                if old_size > 0:
                    ratio = new_size / old_size
                    if ratio < 0.90:
                        logger.warning(
                            t(
                                "logs.parser.size_shrink_warning",
                                old_size=old_size,
                                new_size=new_size,
                                ratio="%.1f%%" % (ratio * 100),
                            )
                        )

            # backup before write
            if cloud_path.exists():
                BackupManager().create_backup(cloud_path)

            with open(self.cloud_storage_path, "w", encoding="utf-8") as f:
                f.write(new_json)

            self._file_mtime = os.path.getmtime(self.cloud_storage_path)
            self.modified = False
            self._deleted_keys.clear()
            return True

        except OSError as e:
            logger.error(t("logs.parser.save_cloud_error"))
            logger.debug(t("logs.parser.error_details", error=e))
            return False

    def get_all_categories(self):
        # return all category names
        return [c.get("name", "") for c in self.collections if c.get("name")]

    @staticmethod
    def _get_collection_apps(col):
        # extract app IDs from collection (handles 'added' and 'apps' keys)
        apps = col.get("added", col.get("apps", []))
        return apps if isinstance(apps, list) else []

    @staticmethod
    def _to_app_id_int(app_id):
        # safely convert app_id to int, return None on failure
        try:
            return int(app_id)
        except (ValueError, TypeError):
            return None

    def get_app_categories(self, app_id):
        # get categories for specific app
        aid = self._to_app_id_int(app_id)
        if aid is None:
            return []

        cats = []
        for col in self.collections:
            apps = self._get_collection_apps(col)
            if aid in apps:
                cats.append(col.get("name", ""))
        return cats

    def set_app_categories(self, app_id, categories):
        # set categories for app
        aid = self._to_app_id_int(app_id)
        if aid is None:
            return  # silently skip invalid IDs

        # remove from all collections first
        for col in self.collections:
            apps = self._get_collection_apps(col)
            if aid in apps:
                apps.remove(aid)

        # add to specified categories
        for cat_name in categories:
            col = None
            for c in self.collections:
                if c.get("name") == cat_name:
                    col = c
                    break

            if not col:
                cid = "from-tag-%s" % cat_name
                col = {"id": cid, "name": cat_name, "added": [], "removed": []}
                self.collections.append(col)

            apps = self._get_collection_apps(col)
            if aid not in apps:
                apps.append(aid)

            if "added" not in col:
                col["added"] = apps

        self.modified = True

    def add_app_category(self, app_id, category):
        # add single category to app
        cats = self.get_app_categories(app_id)
        if category not in cats:
            cats.append(category)
            self.set_app_categories(app_id, cats)

    def remove_app_category(self, app_id, category):
        # remove category from app
        cats = self.get_app_categories(app_id)
        if category in cats:
            cats.remove(category)
            self.set_app_categories(app_id, cats)

    def delete_category(self, category):
        # delete category completely
        for col in self.collections:
            if col.get("name") == category:
                cid = col.get("id", "")
                if cid:
                    self._deleted_keys.add("user-collections.%s" % cid)
        self.collections = [c for c in self.collections if c.get("name") != category]
        self.modified = True

    def create_empty_collection(self, name):
        # create empty collection (safe way)
        cid = "from-tag-%s" % name
        self.collections.append({"id": cid, "name": name, "added": [], "removed": []})
        self.modified = True

    def rename_category(self, old_name, new_name):
        # rename category
        for col in self.collections:
            if col.get("name") == old_name:
                col["name"] = new_name
                col["id"] = "from-tag-%s" % new_name
                self.modified = True
                break

    def get_all_app_ids(self):
        # get all app IDs from all collections
        ids = set()
        for col in self.collections:
            ids.update(str(a) for a in self._get_collection_apps(col))
        return list(ids)

    @staticmethod
    def get_hidden_apps():
        # hidden apps not supported in cloud storage
        return []

    @staticmethod
    def set_app_hidden(app_id, hidden):
        # hidden status not supported here (stored in localconfig.vdf)
        pass

    def remove_app(self, app_id):
        # remove app from all collections
        aid = self._to_app_id_int(app_id)
        if aid is None:
            return False

        removed = False
        for col in self.collections:
            apps = self._get_collection_apps(col)
            if aid in apps:
                apps.remove(aid)
                removed = True

        if removed:
            self.modified = True
        return removed

    @staticmethod
    def _normalize_collection_name(name):
        # normalize name for fuzzy matching (strip case, spaces, etc)
        return name.lower().replace("-", "").replace(" ", "").replace("_", "")

    def get_duplicate_groups(self):
        # find collections with same normalized name
        from collections import defaultdict

        groups = defaultdict(list)
        for col in self.collections:
            name = col.get("name", "")
            if name:
                key = self._normalize_collection_name(name)
                groups[key].append(col)

        result = {}
        for _key, colls in groups.items():
            if len(colls) >= 2:
                rep = colls[0].get("name", "")
                result[rep] = colls
        return result

    def remove_duplicate_collections(self):
        # remove duplicates without merging (WARNING: drops games!)
        seen = {}
        dups = []

        for col in self.collections:
            name = col.get("name", "")
            if name in seen:
                dups.append(col)
            else:
                seen[name] = col

        for dup in dups:
            cid = dup.get("id", "")
            if cid:
                self._deleted_keys.add("user-collections.%s" % cid)
            self.collections.remove(dup)

        if dups:
            self.modified = True

        return len(dups)
