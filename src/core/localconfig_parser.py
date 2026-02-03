# src/core/localconfig_parser.py

"""
Parses and modifies Steam's localconfig.vdf file.

This module provides functionality to read, modify, and write Steam's localconfig.vdf
(or sharedconfig.vdf) file, which stores user-specific game data like categories,
tags, and hidden status. It integrates with BackupManager for automatic backups.

Supports BOTH old (tags) and new (user-collections) Steam formats for maximum compatibility.
"""

import vdf
import json
from pathlib import Path
from typing import Dict, List, Optional
from src.utils.i18n import t
from src.core.backup_manager import BackupManager


class LocalConfigParser:
    """
    Parser for Steam's localconfig.vdf file.

    This class handles reading and writing Steam's localconfig.vdf file using
    the vdf library. It provides methods to manage game categories, tags, and
    hidden status, with automatic backup support.

    Supports BOTH formats:
    - OLD: Categories in Apps/tags (pre-2024)
    - NEW: Categories in user-collections (2024+)
    """

    def __init__(self, config_path: Path):
        """
        Initializes the LocalConfigParser.

        Args:
            config_path (Path): Path to the localconfig.vdf (or sharedconfig.vdf) file.
        """
        self.config_path = config_path
        self.data: Dict = {}
        self.apps: Dict = {}
        self.collections: List[Dict] = []  # NEW: user-collections
        self.modified = False
        self.use_new_format = False  # Auto-detect format

    def load(self) -> bool:
        """
        Loads the localconfig.vdf file into memory.

        This method reads the VDF file and navigates to the Apps section where
        game-specific data (categories, hidden status) is stored.

        Also loads user-collections if present (new Steam format).

        Returns:
            bool: True if loaded successfully, False otherwise.
        """
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                self.data = vdf.load(f)

            # Navigate to Apps section structure:
            # UserLocalConfigStore -> Software -> Valve -> Steam -> Apps
            try:
                steam_section = (self.data.get('UserLocalConfigStore', {})
                                 .get('Software', {})
                                 .get('Valve', {})
                                 .get('Steam', {}))

                self.apps = steam_section.get('Apps', {})

                # NEW: Load user-collections if present
                user_collections_str = steam_section.get('user-collections', '{}')
                self._load_user_collections(user_collections_str)

            except KeyError:
                print(t('logs.parser.apps_not_found'))
                self.apps = {}
                self.collections = []

            return True

        except FileNotFoundError:
            print(t('logs.parser.file_not_found', path=self.config_path))
            return False
        except Exception as e:
            print(t('logs.config.load_error', error=e))
            return False

    def _load_user_collections(self, collections_str: str):
        """
        Loads user-collections from JSON string.

        Args:
            collections_str: JSON string from user-collections field
        """
        try:
            if collections_str and collections_str != '{}':
                collections_data = json.loads(collections_str)
                self.collections = collections_data.get('collections', [])
                self.use_new_format = True
            else:
                self.collections = []
                # Check if we have old format (tags)
                has_tags = any('tags' in app_data for app_data in self.apps.values())
                self.use_new_format = not has_tags
        except json.JSONDecodeError as e:
            print(f"[ERROR] Failed to parse user-collections: {e}")
            self.collections = []
            self.use_new_format = False

    def save(self, create_backup: bool = True) -> bool:
        """
        Saves the current data back to the localconfig.vdf file.

        This method writes the modified data back to disk. If create_backup is True,
        it uses BackupManager to create a timestamped backup with automatic rotation.

        Automatically migrates from old (tags) to new (user-collections) format if needed.

        Args:
            create_backup (bool): Whether to create a rolling backup before saving.

        Returns:
            bool: True if saved successfully, False otherwise.
        """
        if not self.modified:
            return True

        if create_backup:
            # Use BackupManager for rotation and timestamp
            backup_manager = BackupManager()
            # This creates e.g. localconfig_20241022_1530.vdf
            # And automatically deletes the oldest ones when the limit is reached.
            backup_manager.create_backup(self.config_path)

        try:
            # Migrate to new format if needed (only if collections are empty!)
            # This prevents overwriting manually modified collections
            if self.use_new_format and not self.collections:
                self._migrate_to_user_collections()

            # Save user-collections
            self._save_user_collections()

            with open(self.config_path, 'w', encoding='utf-8') as f:
                vdf.dump(self.data, f, pretty=True)
            self.modified = False
            return True
        except OSError as e:
            print(t('logs.config.save_error', error=e))
            return False

    def _migrate_to_user_collections(self):
        """
        Migrates from old tags format to new user-collections format.

        This creates collections from existing tags and updates the data structure.
        """
        # Build category -> app_ids mapping from tags
        category_to_apps: Dict[str, List[str]] = {}

        for app_id, app_data in self.apps.items():
            tags = app_data.get('tags', {})
            if isinstance(tags, dict):
                for tag in tags.values():
                    if tag not in category_to_apps:
                        category_to_apps[tag] = []
                    category_to_apps[tag].append(app_id)

        # Create collections from categories
        self.collections = []
        for idx, (category_name, app_ids) in enumerate(sorted(category_to_apps.items())):
            collection = {
                'id': str(idx + 1),
                'name': category_name,
                'added': 0,  # Timestamp (0 = unknown)
                'apps': app_ids
            }
            self.collections.append(collection)

    def _remove_all_user_collections(self, data):
        """
        Recursively removes ALL 'user-collections' keys from the VDF structure.
        
        Steam sometimes has multiple 'user-collections' keys in the file.
        We must remove ALL of them before writing our own!
        
        Args:
            data: Dictionary to recursively search and clean
        """
        if not isinstance(data, dict):
            return
        
        # Remove 'user-collections' from this level
        if 'user-collections' in data:
            del data['user-collections']
        
        # Recursively check all nested dictionaries
        for key, value in list(data.items()):
            if isinstance(value, dict):
                self._remove_all_user_collections(value)
    
    def _save_user_collections(self):
        """
        Saves collections to user-collections field as JSON string.
        
        CRITICAL: Removes ALL existing 'user-collections' keys first!
        """
        try:
            # STEP 1: Remove ALL 'user-collections' keys from entire VDF
            self._remove_all_user_collections(self.data)
            
            # STEP 2: Write our collections to the correct location
            steam_section = (self.data.get('UserLocalConfigStore', {})
                             .get('Software', {})
                             .get('Valve', {})
                             .get('Steam', {}))

            if self.collections:
                collections_data = {'collections': self.collections}
                collections_str = json.dumps(collections_data, separators=(',', ':'))
                steam_section['user-collections'] = collections_str
            else:
                steam_section['user-collections'] = '{}'

        except Exception as e:
            print(f"[ERROR] Failed to save user-collections: {e}")

    def get_all_app_ids(self) -> List[str]:
        """
        Returns a list of all app IDs found in the config.

        Returns:
            List[str]: A list of app IDs as strings.
        """
        return list(self.apps.keys())

    def get_app_categories(self, app_id: str) -> List[str]:
        """
        Retrieves categories/tags for a specific app.

        Supports BOTH old (tags) and new (user-collections) formats.

        Args:
            app_id (str): The Steam app ID.

        Returns:
            List[str]: A list of category names assigned to this app.
        """
        categories = []

        # Try new format first (user-collections)
        if self.collections:
            for collection in self.collections:
                if str(app_id) in collection.get('apps', []):
                    categories.append(collection['name'])

        # Fallback to old format (tags)
        if not categories:
            app_data = self.apps.get(str(app_id), {})
            tags = app_data.get('tags', {})
            if isinstance(tags, dict):
                categories = list(tags.values())

        return categories

    def set_app_categories(self, app_id: str, categories: List[str]):
        """
        Overwrites all categories for a specific app.

        This method replaces the existing categories with the provided list.
        Updates BOTH old (tags) and new (user-collections) formats for compatibility.

        Args:
            app_id (str): The Steam app ID.
            categories (List[str]): A list of new category names to assign.
        """
        app_id = str(app_id)

        # Update old format (tags) for backward compatibility
        if app_id not in self.apps:
            self.apps[app_id] = {}

        tags_dict = {str(i): cat for i, cat in enumerate(categories)}
        self.apps[app_id]['tags'] = tags_dict

        # Update new format (user-collections)
        # Remove app from all collections
        for collection in self.collections:
            if app_id in collection.get('apps', []):
                collection['apps'].remove(app_id)

        # Add app to specified collections
        for category in categories:
            # Find or create collection
            collection = self._find_or_create_collection(category)
            if app_id not in collection['apps']:
                collection['apps'].append(app_id)

        self.modified = True

    def _find_or_create_collection(self, name: str) -> Dict:
        """
        Finds an existing collection by name or creates a new one.

        Args:
            name: Collection name

        Returns:
            Collection dictionary
        """
        for collection in self.collections:
            if collection['name'] == name:
                return collection

        # Create new collection
        new_id = str(len(self.collections) + 1)
        collection = {
            'id': new_id,
            'name': name,
            'added': 0,
            'apps': []
        }
        self.collections.append(collection)
        return collection

    def add_app_category(self, app_id: str, category: str):
        """
        Adds a single category to an app if not already present.

        Args:
            app_id (str): The Steam app ID.
            category (str): The category name to add.
        """
        categories = self.get_app_categories(app_id)
        if category not in categories:
            categories.append(category)
            self.set_app_categories(app_id, categories)

    def remove_app_category(self, app_id: str, category: str):
        """
        Removes a single category from an app.

        Args:
            app_id (str): The Steam app ID.
            category (str): The category name to remove.
        """
        categories = self.get_app_categories(app_id)
        if category in categories:
            categories.remove(category)
            self.set_app_categories(app_id, categories)

    def remove_app(self, app_id: str) -> bool:
        """
        Removes an app entry completely from the local configuration.

        Useful for removing 'ghost' entries that no longer exist in Steam.

        Args:
            app_id (str): The Steam app ID to remove.

        Returns:
            bool: True if the app was removed, False if not found.
        """
        if self.apps and app_id in self.apps:
            del self.apps[app_id]

            # Remove from collections
            for collection in self.collections:
                if app_id in collection.get('apps', []):
                    collection['apps'].remove(app_id)

            self.modified = True
            return True
        return False

    def get_apps_in_category(self, category: str) -> List[str]:
        """
        Returns all app IDs belonging to a specific category.

        Args:
            category (str): The category name to search for.

        Returns:
            List[str]: A list of app IDs that have this category.
        """
        # Try new format first
        for collection in self.collections:
            if collection['name'] == category:
                return collection.get('apps', [])

        # Fallback to old format
        apps = []
        for app_id in self.apps:
            if category in self.get_app_categories(app_id):
                apps.append(app_id)
        return apps

    def get_all_categories(self) -> List[str]:
        """
        Returns a list of all unique category names.

        Returns:
            List[str]: List of all category names
        """
        categories = set()

        # From new format
        for collection in self.collections:
            categories.add(collection['name'])

        # From old format (fallback)
        for app_data in self.apps.values():
            tags = app_data.get('tags', {})
            if isinstance(tags, dict):
                categories.update(tags.values())

        return sorted(categories)

    def rename_category(self, old_name: str, new_name: str):
        """
        Renames a category across all apps.

        This method finds all apps with the old category name and replaces it
        with the new name. Updates BOTH old and new formats.

        Args:
            old_name (str): The current category name.
            new_name (str): The new category name.
        """
        # Update new format
        for collection in self.collections:
            if collection['name'] == old_name:
                collection['name'] = new_name

        # Update old format
        for app_id in self.apps:
            categories = self.get_app_categories(app_id)
            if old_name in categories:
                categories = [new_name if c == old_name else c for c in categories]
                self.set_app_categories(app_id, categories)

        self.modified = True

    def create_empty_collection(self, name: str) -> None:
        """Creates an empty collection without any app IDs.

        Adds the collection to the internal list so that it persists
        on the next save, even though no games are assigned yet.

        Args:
            name: The display name for the new collection.
        """
        # Avoid duplicate
        for collection in self.collections:
            if collection.get('name') == name:
                return

        self.collections.append({
            'id': str(len(self.collections) + 1),
            'name': name,
            'apps': []
        })
        self.modified = True

    def delete_category(self, category: str):
        """
        Removes a category from all apps.

        Args:
            category (str): The category name to delete.
        """
        # Remove from new format
        self.collections = [c for c in self.collections if c['name'] != category]

        # Remove from old format
        for app_id in self.apps:
            self.remove_app_category(app_id, category)

        self.modified = True

    def get_app_data(self, app_id: str) -> Optional[Dict]:
        """
        Returns the raw dictionary data for an app.

        Args:
            app_id (str): The Steam app ID.

        Returns:
            Optional[Dict]: The raw app data dictionary, or None if not found.
        """
        return self.apps.get(app_id)

    def set_app_data(self, app_id: str, data: Dict):
        """
        Sets the raw dictionary data for an app.

        Args:
            app_id (str): The Steam app ID.
            data (Dict): The raw app data dictionary to set.
        """
        self.apps[app_id] = data
        self.modified = True

    def get_uncategorized_apps(self) -> List[str]:
        """
        Returns app IDs that have no categories (or only 'favorite').

        Returns:
            List[str]: A list of app IDs with no meaningful categories.
        """
        uncategorized = []
        for app_id in self.apps:
            categories = self.get_app_categories(app_id)
            if not categories or categories == ['favorite']:
                uncategorized.append(app_id)
        return uncategorized

    # --- HIDDEN APP SUPPORT ---

    def get_hidden_apps(self) -> List[str]:
        """
        Returns a list of all hidden app IDs.

        Steam stores the hidden status as a "Hidden" key with value "1" (string) or 1 (int).

        Returns:
            List[str]: A list of app IDs that are marked as hidden.
        """
        hidden_apps = []
        for app_id, data in self.apps.items():
            # Steam stores Hidden as "1" (String) or 1 (Int)
            if 'Hidden' in data and str(data['Hidden']) == "1":
                hidden_apps.append(app_id)
        return hidden_apps

    def set_app_hidden(self, app_id: str, hidden: bool):
        """
        Sets or removes the hidden status for a game.

        Args:
            app_id (str): The Steam app ID.
            hidden (bool): True to hide the game, False to unhide it.
        """
        try:
            if str(app_id) not in self.apps:
                self.apps[str(app_id)] = {}

            if hidden:
                self.apps[str(app_id)]['Hidden'] = "1"
            else:
                # Remove key if no longer hidden
                if 'Hidden' in self.apps[str(app_id)]:
                    del self.apps[str(app_id)]['Hidden']

            self.modified = True
        except Exception as e:
            print(t('logs.parser.hidden_error', error=str(e)))
