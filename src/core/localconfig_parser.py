# src/core/localconfig_parser.py

"""
Parses and modifies Steam's localconfig.vdf file.

This module provides functionality to read, modify, and write Steam's localconfig.vdf
(or sharedconfig.vdf) file, which stores user-specific game data like categories,
tags, and hidden status. It integrates with BackupManager for automatic backups.
"""

import vdf
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
        self.modified = False

    def load(self) -> bool:
        """
        Loads the localconfig.vdf file into memory.

        This method reads the VDF file and navigates to the Apps section where
        game-specific data (categories, hidden status) is stored.

        Returns:
            bool: True if loaded successfully, False otherwise.
        """
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                self.data = vdf.load(f)

            # Navigate to Apps section structure:
            # UserLocalConfigStore -> Software -> Valve -> Steam -> Apps
            try:
                self.apps = (self.data.get('UserLocalConfigStore', {})
                             .get('Software', {})
                             .get('Valve', {})
                             .get('Steam', {})
                             .get('Apps', {}))
            except KeyError:
                print(t('logs.parser.apps_not_found'))
                self.apps = {}

            return True

        except FileNotFoundError:
            print(t('logs.parser.file_not_found', path=self.config_path))
            return False
        except Exception as e:
            print(t('logs.config.load_error', error=e))
            return False

    def save(self, create_backup: bool = True) -> bool:
        """
        Saves the current data back to the localconfig.vdf file.

        This method writes the modified data back to disk. If create_backup is True,
        it uses BackupManager to create a timestamped backup with automatic rotation.

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
            with open(self.config_path, 'w', encoding='utf-8') as f:
                vdf.dump(self.data, f, pretty=True)
            self.modified = False
            return True
        except OSError as e:
            print(t('logs.config.save_error', error=e))
            return False

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

        Steam stores categories as a dictionary with numeric keys (e.g., {"0": "Action", "1": "RPG"}).
        This method extracts and returns the category names as a list.

        Args:
            app_id (str): The Steam app ID.

        Returns:
            List[str]: A list of category names assigned to this app.
        """
        app_data = self.apps.get(str(app_id), {})
        tags = app_data.get('tags', {})

        # Tags are stored as a dictionary {"0": "Tag", "1": "Tag"} or list
        if isinstance(tags, dict):
            return list(tags.values())
        return []

    def set_app_categories(self, app_id: str, categories: List[str]):
        """
        Overwrites all categories for a specific app.

        This method replaces the existing categories with the provided list.
        Categories are stored in Steam's format as a dictionary with numeric keys.

        Args:
            app_id (str): The Steam app ID.
            categories (List[str]): A list of new category names to assign.
        """
        if str(app_id) not in self.apps:
            self.apps[str(app_id)] = {}

        # Steam stores tags as Dict {"0": "Tag1", "1": "Tag2"}
        tags_dict = {str(i): cat for i, cat in enumerate(categories)}
        self.apps[str(app_id)]['tags'] = tags_dict
        self.modified = True

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
        apps = []
        for app_id in self.apps:
            if category in self.get_app_categories(app_id):
                apps.append(app_id)
        return apps

    def rename_category(self, old_name: str, new_name: str):
        """
        Renames a category across all apps.

        This method finds all apps with the old category name and replaces it
        with the new name.

        Args:
            old_name (str): The current category name.
            new_name (str): The new category name.
        """
        for app_id in self.apps:
            categories = self.get_app_categories(app_id)
            if old_name in categories:
                # Replace old name with new name
                categories = [new_name if c == old_name else c for c in categories]
                self.set_app_categories(app_id, categories)

    def delete_category(self, category: str):
        """
        Removes a category from all apps.

        Args:
            category (str): The category name to delete.
        """
        for app_id in self.apps:
            self.remove_app_category(app_id, category)

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
