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

import json
import os
import time
from pathlib import Path
from typing import Dict, List

from src.core.backup_manager import BackupManager


class CloudStorageParser:
    """Parser for Steam's cloud-storage-namespace-1.json collections format."""

    # Virtual UI-only categories that should NEVER be written to cloud storage
    # These are calculated dynamically by the UI
    VIRTUAL_CATEGORIES = {
        'Unkategorisiert', 'Uncategorized',  # Shows games not in any collection
        'Alle Spiele', 'All Games',          # Shows all games
    }
    
    # Special Steam collections IDs (like Depressurizer does it!)
    # These ARE saved in cloud-storage with special IDs
    SPECIAL_COLLECTION_IDS = {
        'Favoriten': 'favorite',
        'Favorites': 'favorite',
        'Versteckt': 'hidden',
        'Hidden': 'hidden',
    }

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
            steam_path, 'userdata', user_id, 'config', 'cloudstorage',
            'cloud-storage-namespace-1.json'
        )
        self.data: List = []
        self.collections: List[Dict] = []
        self.modified = False

    def load(self) -> bool:
        """
        Load collections from cloud storage JSON file.

        Returns:
            True if successful, False otherwise
        """
        try:
            if not os.path.exists(self.cloud_storage_path):
                return False

            with open(self.cloud_storage_path, 'r', encoding='utf-8') as f:
                self.data = json.load(f)

            if not isinstance(self.data, list):
                print(f"[ERROR] Cloud storage data is not a list!")
                return False

            # Extract collections
            self.collections = []
            for item in self.data:
                if len(item) == 2 and isinstance(item[1], dict):
                    key = item[1].get('key', '')
                    if key.startswith('user-collections.'):
                        # Parse the value JSON
                        value_str = item[1].get('value', '{}')
                        if value_str and value_str != '{}':
                            try:
                                collection_data = json.loads(value_str)
                                self.collections.append(collection_data)
                            except json.JSONDecodeError:
                                print(f"[WARN] Failed to parse collection: {key}")

            return True

        except FileNotFoundError:
            print(f"[ERROR] Cloud storage file not found: {self.cloud_storage_path}")
            return False
        except Exception as e:
            print(f"[ERROR] Failed to load cloud storage: {e}")
            return False

    def save(self) -> bool:
        """
        Save collections to cloud storage JSON file.

        Returns:
            True if successful, False otherwise
        """
        try:
            # Remove all existing collection items
            self.data = [item for item in self.data
                         if not (len(item) == 2 and isinstance(item[1], dict) and
                                 item[1].get('key', '').startswith('user-collections.'))]

            # Sanitize: 'added' must always be a list of ints.
            # Migrated collections sometimes have 'added': 0 (a bare timestamp).
            for collection in self.collections:
                added = collection.get('added', collection.get('apps', []))
                if not isinstance(added, list):
                    collection['added'] = []
                    collection.setdefault('apps', [])

            # Add our collections
            timestamp = int(time.time())
            for collection in self.collections:
                collection_id = collection.get('id', '')
                collection_name = collection.get('name', '')

                # CRITICAL FIX 1: Skip VIRTUAL categories!
                # These should never be written to cloud storage
                if collection_name in self.VIRTUAL_CATEGORIES:
                    continue
                
                # CRITICAL FIX 2: Skip EMPTY special collections (favorites/hidden)!
                # Steam only shows these if they contain games
                added_apps = collection.get('added', collection.get('apps', []))
                if collection_name in self.SPECIAL_COLLECTION_IDS and not added_apps:
                    continue  # Don't save empty favorites/hidden

                # CRITICAL FIX 3: Use correct Steam ID for special collections (like Depressurizer!)
                # Depressurizer uses "favorite" and "hidden" (not "favorites"!)
                if collection_name in self.SPECIAL_COLLECTION_IDS:
                    special_id = self.SPECIAL_COLLECTION_IDS[collection_name]
                    collection_id = special_id
                    collection['id'] = special_id
                    key = f"user-collections.{special_id}"
                elif not collection_id.startswith('from-tag-') and not collection_id.startswith('uc-'):
                    # Regular user collection - ensure from-tag- prefix
                    collection_id = f"from-tag-{collection_name}"
                    collection['id'] = collection_id
                    key = f"user-collections.{collection_id}"
                else:
                    # Already has correct ID
                    key = f"user-collections.{collection_id}"

                # CRITICAL FIX 4: Build value JSON with filterSpec preservation!
                # This keeps dynamic collections dynamic across saves
                value_data = {
                    'id': collection_id,
                    'name': collection_name,
                    'added': added_apps,
                    'removed': collection.get('removed', [])
                }

                # Preserve filterSpec for dynamic collections!
                if 'filterSpec' in collection:
                    value_data['filterSpec'] = collection['filterSpec']

                value_str = json.dumps(value_data, separators=(',', ':'))

                # Create item
                item = [
                    key,
                    {
                        'key': key,
                        'timestamp': timestamp,
                        'value': value_str,
                        'version': str(int(time.time() % 10000))
                    }
                ]

                self.data.append(item)

            # Create backup before writing
            cloud_path = Path(self.cloud_storage_path)
            if cloud_path.exists():
                backup_manager = BackupManager()
                backup_manager.create_backup(cloud_path)

            # Write to file
            with open(self.cloud_storage_path, 'w', encoding='utf-8') as f:
                json.dump(self.data, f, indent=2, ensure_ascii=False)

            self.modified = False
            return True


        except OSError as e:
            from src.utils.i18n import t
            print(t('logs.parser.save_cloud_error'))
            print(f"[DEBUG] Error details: {e}")  # ← Nutze 'e'
            return False

    def get_all_categories(self) -> List[str]:
        """
        Get all unique category names from collections.

        Returns:
            List of category names
        """
        return [c.get('name', '') for c in self.collections if c.get('name')]

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

    def get_app_categories(self, app_id: str) -> List[str]:
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
            apps = collection.get('added', collection.get('apps', []))
            # Guard: 'added' can be a bare timestamp int (0) in migrated data
            if not isinstance(apps, list):
                continue
            if app_id_int in apps:
                categories.append(collection.get('name', ''))

        return categories

    def set_app_categories(self, app_id: str, categories: List[str]):
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
            apps = collection.get('added', collection.get('apps', []))
            if not isinstance(apps, list):
                continue
            if app_id_int in apps:
                apps.remove(app_id_int)

        # Add app to specified collections
        for category_name in categories:
            # Find or create collection
            collection = None
            for c in self.collections:
                if c.get('name') == category_name:
                    collection = c
                    break

            if not collection:
                # Create new collection
                collection_id = f"from-tag-{category_name}"
                collection = {
                    'id': collection_id,
                    'name': category_name,
                    'added': [],
                    'removed': []
                }
                self.collections.append(collection)

            # Add app
            apps = collection.get('added', collection.get('apps', []))
            if app_id_int not in apps:
                apps.append(app_id_int)

            # Ensure 'added' key exists
            if 'added' not in collection:
                collection['added'] = apps

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

        Args:
            category: Category name
        """
        self.collections = [c for c in self.collections if c.get('name') != category]
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
        self.collections.append({
            'id': collection_id,
            'name': name,
            'added': [],
            'removed': []
        })
        self.modified = True

    def rename_category(self, old_name: str, new_name: str):
        """
        Rename a category.

        Args:
            old_name: Old category name
            new_name: New category name
        """
        for collection in self.collections:
            if collection.get('name') == old_name:
                collection['name'] = new_name
                collection['id'] = f"from-tag-{new_name}"
                self.modified = True
                break

    def get_all_app_ids(self) -> List[str]:
        """
        Get all app IDs from all collections.

        Returns:
            List of app IDs as strings
        """
        app_ids = set()
        for collection in self.collections:
            apps = collection.get('added', collection.get('apps', []))
            app_ids.update(str(app_id) for app_id in apps)
        return list(app_ids)

    @staticmethod
    def get_hidden_apps() -> List[str]:
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
            apps = collection.get('added', collection.get('apps', []))
            if not isinstance(apps, list):
                continue
            if app_id_int in apps:
                apps.remove(app_id_int)
                removed = True

        if removed:
            self.modified = True

        return removed

    def remove_duplicate_collections(self) -> int:
        """Remove duplicate collections with same name.

        Keeps the first occurrence of each name, removes subsequent duplicates.

        Returns:
            Number of duplicates removed
        """
        seen = {}
        duplicates = []

        for collection in self.collections:
            name = collection.get('name', '')
            if name in seen:
                duplicates.append(collection)
            else:
                seen[name] = collection

        # Remove duplicates
        for dup in duplicates:
            self.collections.remove(dup)

        if duplicates:
            self.modified = True

        return len(duplicates)