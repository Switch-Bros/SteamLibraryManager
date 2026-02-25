# src/core/cloud_storage_parser.py

"""
Steam Cloud Storage Parser

Handles reading and writing Steam collections from cloud-storage-namespace-1.json.

Since 2024, Steam stores collections in:
~/.steam/steam/userdata/<USER_ID>/config/cloudstorage/cloud-storage-namespace-1.json

Format:
[
  "user-collections.from-tag-<n>",
  {
    "key": "user-collections.from-tag-<n>",
    "timestamp": <UNIX_TIMESTAMP>,
    "value": "{\"id\":\"from-tag-<n>\",\"name\":\"<n>\",\"added\":[<APP_IDS>],\"removed\":[]}",
    "version": "<VERSION>"
  }
]
"""

from __future__ import annotations

import json
import logging
import os
import time
from pathlib import Path

from src.core.backup_manager import BackupManager
from src.utils.i18n import t

logger = logging.getLogger("steamlibmgr.cloud_parser")


__all__ = ["CloudStorageParser"]


class CloudStorageParser:
    """Parser for Steam's cloud-storage-namespace-1.json collections format."""

    @staticmethod
    def _get_virtual_categories() -> set[str]:
        """Returns virtual UI-only category names that should NEVER be written to cloud storage.

        These are calculated dynamically using the current locale so that
        any translation of 'Uncategorized' or 'All Games' is recognised.
        """
        return {
            t("categories.uncategorized"),
            t("categories.all_games"),
            t("categories.soundtracks"),
            t("categories.tools"),
            t("categories.software"),
            t("categories.videos"),
        }

    @staticmethod
    def _get_special_collection_ids() -> dict[str, str]:
        """Maps ALL known display names to Steam internal IDs.

        Includes hardcoded names for EN/DE plus current locale to ensure
        collections are recognized regardless of which language created them.

        Steam uses 'favorite' and 'hidden' as internal collection IDs.

        Returns:
            Dict mapping display name to Steam internal ID.
        """
        # TODO v1.2: Refactor to use ONLY collection IDs for system collection
        # detection. Remove hardcoded name matching once all consumers use IDs.
        mapping: dict[str, str] = {
            # Steam internal
            "favorite": "favorite",
            "hidden": "hidden",
            # English
            "Favorites": "favorite",
            "Hidden": "hidden",
            # German
            "Favoriten": "favorite",
            "Versteckt": "hidden",
        }
        # Current locale (may duplicate, dict handles it)
        mapping[t("categories.favorites")] = "favorite"
        mapping[t("categories.hidden")] = "hidden"
        return mapping

    def __init__(self, steam_path: str, user_id: str):
        """
        Initialize the cloud storage parser.

        Args:
            steam_path: Path to Steam installation
            user_id: Steam user ID
        """
        self.steam_path = steam_path
        self.user_id = user_id
        self.cloud_storage_path = os.path.join(
            steam_path, "userdata", user_id, "config", "cloudstorage", "cloud-storage-namespace-1.json"
        )
        self.data: list = []
        self.collections: list[dict] = []
        self.modified = False
        self.had_conflict: bool = False
        self._file_mtime: float = 0.0
        # Track explicitly deleted collections for delta-merge save
        self._deleted_keys: set[str] = set()

    def load(self) -> bool:
        """
        Load collections from cloud storage JSON file.

        Returns:
            True if successful, False otherwise
        """
        try:
            if not os.path.exists(self.cloud_storage_path):
                return False

            with open(self.cloud_storage_path, "r", encoding="utf-8") as f:
                self.data = json.load(f)

            if not isinstance(self.data, list):
                logger.error(t("logs.parser.not_a_list"))
                return False

            # Record mtime for conflict detection
            self._file_mtime = os.path.getmtime(self.cloud_storage_path)

            # Extract collections
            self.collections = []
            for item in self.data:
                if len(item) == 2 and isinstance(item[1], dict):
                    key = item[1].get("key", "")
                    if key.startswith("user-collections."):
                        # Parse the value JSON
                        value_str = item[1].get("value", "{}")
                        if value_str and value_str != "{}":
                            try:
                                collection_data = json.loads(value_str)
                                self.collections.append(collection_data)
                            except json.JSONDecodeError:
                                logger.warning(t("logs.parser.parse_failed", key=key))

            return True

        except FileNotFoundError:
            logger.error(t("logs.parser.cloud_file_not_found", path=self.cloud_storage_path))
            return False
        except Exception as e:
            logger.error(t("logs.parser.load_error", error=e))
            return False

    def has_external_changes(self) -> bool:
        """Check if the cloud storage file was modified externally since last load.

        Compares the current file mtime with the mtime recorded during load().

        Returns:
            True if the file has been modified since last load.
        """
        if not self._file_mtime or not os.path.exists(self.cloud_storage_path):
            return False
        current_mtime = os.path.getmtime(self.cloud_storage_path)
        return current_mtime != self._file_mtime

    def mark_all_managed_as_deleted(self) -> None:
        """Mark all current collections for deletion during next save.

        Used for full replacement operations (e.g. profile restore) where
        the entire collection set is replaced and old managed collections
        should not be preserved.
        """
        for collection in self.collections:
            col_id = collection.get("id", "")
            if col_id:
                self._deleted_keys.add(f"user-collections.{col_id}")

    def save(self) -> bool:
        """Save collections using delta-merge approach.

        NEVER overwrites the entire file. Instead:
        1. Builds set of collection-keys this app actively manages
        2. Removes ONLY managed + explicitly deleted keys from data
        3. Preserves everything the app didn't touch
        4. Writes managed collections back
        5. Size-check as safety net

        Sets ``had_conflict`` to True if external changes were detected
        before saving.  The UI layer can inspect this after a successful
        save to inform the user.

        Returns:
            True if successful, False otherwise.
        """
        try:
            # Check for external modifications and expose to callers
            self.had_conflict = self.has_external_changes()
            if self.had_conflict:
                logger.warning(t("logs.parser.external_change_detected"))

            # === DELTA-MERGE: Build set of keys we actively manage ===
            managed_keys: set[str] = set()
            for collection in self.collections:
                col_id = collection.get("id", "")
                if col_id:
                    managed_keys.add(f"user-collections.{col_id}")

            # === Remove ONLY managed + deleted keys (preserve everything else!) ===
            preserved_items: list = []
            preserved_collection_count = 0

            for item in self.data:
                if len(item) == 2 and isinstance(item[1], dict):
                    key = item[1].get("key", "")
                    if key.startswith("user-collections."):
                        if key in managed_keys or key in self._deleted_keys:
                            continue  # We'll rewrite managed ones below
                        else:
                            preserved_collection_count += 1
                            preserved_items.append(item)  # DON'T TOUCH!
                            continue
                preserved_items.append(item)

            self.data = preserved_items

            if preserved_collection_count > 0 or self._deleted_keys:
                logger.info(
                    t(
                        "logs.parser.delta_merge_stats",
                        managed=len(managed_keys),
                        deleted=len(self._deleted_keys),
                        preserved=preserved_collection_count,
                    )
                )

            # Sanitize: 'added' must always be a list of ints.
            # Migrated collections sometimes have 'added': 0 (a bare timestamp).
            for collection in self.collections:
                raw_added = collection.get("added", collection.get("apps"))
                if not isinstance(raw_added, list):
                    collection["added"] = []
                    collection.setdefault("apps", [])

            # Add our collections
            timestamp = int(time.time())
            for collection in self.collections:
                collection_id = collection.get("id", "")
                collection_name = collection.get("name", "")

                # CRITICAL FIX 1: Skip VIRTUAL categories!
                # These should never be written to cloud storage
                virtual = self._get_virtual_categories()
                if collection_name in virtual:
                    continue

                # CRITICAL FIX 2: Skip EMPTY special collections (favorites/hidden)!
                # Steam only shows these if they contain games
                added_apps = self._get_collection_apps(collection)
                special_ids = self._get_special_collection_ids()
                if collection_name in special_ids and not added_apps:
                    continue  # Don't save empty favorites/hidden

                # CRITICAL FIX 3: Use correct Steam ID for special collections (like Depressurizer!)
                # Depressurizer uses "favorite" and "hidden" (not "favorites"!)
                if collection_name in special_ids:
                    special_id = special_ids[collection_name]
                    collection_id = special_id
                    collection["id"] = special_id
                    key = f"user-collections.{special_id}"
                elif not collection_id.startswith("from-tag-") and not collection_id.startswith("uc-"):
                    # Regular user collection - ensure from-tag- prefix
                    collection_id = f"from-tag-{collection_name}"
                    collection["id"] = collection_id
                    key = f"user-collections.{collection_id}"
                else:
                    # Already has correct ID
                    key = f"user-collections.{collection_id}"

                # CRITICAL FIX 4: Build value JSON with filterSpec preservation!
                # This keeps dynamic collections dynamic across saves
                value_data = {
                    "id": collection_id,
                    "name": collection_name,
                    "added": added_apps,
                    "removed": collection.get("removed", []),
                }

                # Preserve filterSpec for dynamic collections!
                if "filterSpec" in collection:
                    value_data["filterSpec"] = collection["filterSpec"]

                value_str = json.dumps(value_data, separators=(",", ":"))

                # Create item
                item = [
                    key,
                    {"key": key, "timestamp": timestamp, "value": value_str, "version": str(int(time.time() % 10000))},
                ]

                self.data.append(item)

            # === SIZE-CHECK SAFETY NET ===
            new_json = json.dumps(self.data, indent=2, ensure_ascii=False)
            cloud_path = Path(self.cloud_storage_path)
            if cloud_path.exists():
                old_size = cloud_path.stat().st_size
                new_size = len(new_json.encode("utf-8"))
                if old_size > 0:
                    size_ratio = new_size / old_size
                    if size_ratio < 0.90:
                        logger.warning(
                            t(
                                "logs.parser.size_shrink_warning",
                                old_size=old_size,
                                new_size=new_size,
                                ratio=f"{size_ratio:.1%}",
                            )
                        )

            # Create backup before writing
            if cloud_path.exists():
                backup_manager = BackupManager()
                backup_manager.create_backup(cloud_path)

            # Write to file
            with open(self.cloud_storage_path, "w", encoding="utf-8") as f:
                f.write(new_json)

            # Update recorded mtime so subsequent saves don't false-positive
            self._file_mtime = os.path.getmtime(self.cloud_storage_path)
            self.modified = False
            self._deleted_keys.clear()  # Reset after successful save
            return True

        except OSError as e:
            logger.error(t("logs.parser.save_cloud_error"))
            logger.debug(t("logs.parser.error_details", error=e))
            return False

    def get_all_categories(self) -> list[str]:
        """
        Get all unique category names from collections.

        Returns:
            List of category names
        """
        return [c.get("name", "") for c in self.collections if c.get("name")]

    @staticmethod
    def _get_collection_apps(collection: dict) -> list[int]:
        """Extracts app IDs from a collection dict (handles both 'added' and 'apps' keys).

        Args:
            collection: Cloud collection dictionary.

        Returns:
            List of app IDs, empty list on invalid data.
        """
        apps = collection.get("added", collection.get("apps", []))
        return apps if isinstance(apps, list) else []

    @staticmethod
    def _to_app_id_int(app_id) -> int | None:
        """Safely converts an app-id value to int.

        Returns None when the value is empty, non-numeric, or otherwise
        un-convertible.  This guards every ``int(app_id)`` call-site so
        that corrupt or missing IDs never crash the parser.

        Args:
            app_id: Raw app-id (str, int, or anything else).

        Returns:
            The integer app-id, or None on failure.
        """
        try:
            return int(app_id)
        except (ValueError, TypeError):
            return None

    def get_app_categories(self, app_id: str) -> list[str]:
        """
        Get categories for a specific app.

        Args:
            app_id: Steam app ID

        Returns:
            List of category names
        """
        app_id_int: int | None = self._to_app_id_int(app_id)
        if app_id_int is None:
            return []

        categories: list[str] = []
        for collection in self.collections:
            apps = self._get_collection_apps(collection)
            if app_id_int in apps:
                categories.append(collection.get("name", ""))

        return categories

    def set_app_categories(self, app_id: str, categories: list[str]):
        """
        Set categories for a specific app.

        Args:
            app_id: Steam app ID
            categories: List of category names
        """
        app_id_int: int | None = self._to_app_id_int(app_id)
        if app_id_int is None:
            return  # silently skip invalid app IDs

        # Remove app from all collections
        for collection in self.collections:
            apps = self._get_collection_apps(collection)
            if app_id_int in apps:
                apps.remove(app_id_int)

        # Add app to specified collections
        for category_name in categories:
            # Find or create collection
            collection = None
            for c in self.collections:
                if c.get("name") == category_name:
                    collection = c
                    break

            if not collection:
                # Create new collection
                collection_id = f"from-tag-{category_name}"
                collection = {"id": collection_id, "name": category_name, "added": [], "removed": []}
                self.collections.append(collection)

            # Add app
            apps = self._get_collection_apps(collection)
            if app_id_int not in apps:
                apps.append(app_id_int)

            # Ensure 'added' key exists
            if "added" not in collection:
                collection["added"] = apps

        self.modified = True

    def add_app_category(self, app_id: str, category: str):
        """
        Add a category to an app.

        Args:
            app_id: Steam app ID
            category: Category name
        """
        categories = self.get_app_categories(app_id)
        if category not in categories:
            categories.append(category)
            self.set_app_categories(app_id, categories)

    def remove_app_category(self, app_id: str, category: str):
        """
        Remove a category from an app.

        Args:
            app_id: Steam app ID
            category: Category name
        """
        categories = self.get_app_categories(app_id)
        if category in categories:
            categories.remove(category)
            self.set_app_categories(app_id, categories)

    def delete_category(self, category: str):
        """
        Delete a category completely.

        Tracks the deleted key for delta-merge so save() removes it from
        the cloud storage file instead of silently dropping it.

        Args:
            category: Category name
        """
        for collection in self.collections:
            if collection.get("name") == category:
                col_id = collection.get("id", "")
                if col_id:
                    self._deleted_keys.add(f"user-collections.{col_id}")
        self.collections = [c for c in self.collections if c.get("name") != category]
        self.modified = True

    def create_empty_collection(self, name: str) -> None:
        """Creates an empty collection without any app IDs.

        This is the safe way to create a new collection.  Using
        ``add_app_category("", name)`` would crash because this class
        calls ``int(app_id)`` internally.

        Args:
            name: The display name for the new collection.
        """
        collection_id: str = f"from-tag-{name}"
        self.collections.append({"id": collection_id, "name": name, "added": [], "removed": []})
        self.modified = True

    def rename_category(self, old_name: str, new_name: str):
        """
        Rename a category.

        Args:
            old_name: Old category name
            new_name: New category name
        """
        for collection in self.collections:
            if collection.get("name") == old_name:
                collection["name"] = new_name
                collection["id"] = f"from-tag-{new_name}"
                self.modified = True
                break

    def get_all_app_ids(self) -> list[str]:
        """
        Get all app IDs from all collections.

        Returns:
            List of app IDs as strings
        """
        app_ids = set()
        for collection in self.collections:
            app_ids.update(str(a) for a in self._get_collection_apps(collection))
        return list(app_ids)

    @staticmethod
    def get_hidden_apps() -> list[str]:
        """
        Get hidden apps (not supported in cloud storage).

        Returns:
            Empty list (hidden status is stored in localconfig.vdf, not cloud storage)
        """
        return []

    @staticmethod
    def set_app_hidden(app_id: str, hidden: bool):
        """
        Set app hidden status (not supported in cloud storage).

        Args:
            app_id: Steam app ID
            hidden: True to hide, False to unhide

        Note:
            Hidden status is stored in localconfig.vdf, not cloud storage.
            This method does nothing.
        """
        pass

    def remove_app(self, app_id: str) -> bool:
        """
        Remove app from all collections.

        Args:
            app_id: Steam app ID

        Returns:
            True if app was removed, False otherwise
        """
        app_id_int: int | None = self._to_app_id_int(app_id)
        if app_id_int is None:
            return False

        removed = False
        for collection in self.collections:
            apps = self._get_collection_apps(collection)
            if app_id_int in apps:
                apps.remove(app_id_int)
                removed = True

        if removed:
            self.modified = True

        return removed

    def get_duplicate_groups(self) -> dict[str, list[dict]]:
        """Returns collection names that appear more than once.

        Groups collections by name and returns only those with 2+ occurrences.
        This allows the UI to display each duplicate individually and lets
        the user choose which one to keep during merging.

        Returns:
            Dict mapping collection name to list of collection dicts
            for names with 2+ occurrences.
        """
        from collections import defaultdict

        groups: defaultdict[str, list[dict]] = defaultdict(list)
        for collection in self.collections:
            name = collection.get("name", "")
            if name:
                groups[name].append(collection)
        return {name: colls for name, colls in groups.items() if len(colls) >= 2}

    def remove_duplicate_collections(self) -> int:
        """Remove duplicate collections with same name.

        Keeps the first occurrence of each name, removes subsequent duplicates.

        Returns:
            Number of duplicates removed
        """
        seen = {}
        duplicates = []

        for collection in self.collections:
            name = collection.get("name", "")
            if name in seen:
                duplicates.append(collection)
            else:
                seen[name] = collection

        # Remove duplicates (track keys for delta-merge)
        for dup in duplicates:
            col_id = dup.get("id", "")
            if col_id:
                self._deleted_keys.add(f"user-collections.{col_id}")
            self.collections.remove(dup)

        if duplicates:
            self.modified = True

        return len(duplicates)
