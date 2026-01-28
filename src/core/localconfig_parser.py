"""
localconfig.vdf Parser and Writer
Reads and writes Steam's localconfig.vdf file using the vdf library.
"""

import vdf
import shutil
from pathlib import Path
from typing import Dict, List, Optional
from src.utils.i18n import t


class LocalConfigParser:
    """
    Parser for Steam's localconfig.vdf.
    Handles reading tags, hidden status, and managing categories via the 'vdf' library.
    """

    def __init__(self, config_path: Path):
        """
        Initialize the parser.

        Args:
            config_path (Path): Path to the localconfig.vdf file.
        """
        self.config_path = config_path
        self.data: Dict = {}
        self.apps: Dict = {}
        self.modified = False

    def load(self) -> bool:
        """
        Loads the localconfig.vdf file into memory.

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
                # We use a specific key for this specific structure error
                print(t('logs.parser.apps_not_found'))
                self.apps = {}

            return True

        except FileNotFoundError:
            print(t('logs.parser.file_not_found', path=self.config_path))
            return False
        except Exception as e:
            # Re-use existing config load error from locales
            print(t('logs.config.load_error', error=e))
            return False

    def save(self, create_backup: bool = True) -> bool:
        """
        Saves the current data back to localconfig.vdf.

        Args:
            create_backup (bool): Whether to create a .bak file before saving.

        Returns:
            bool: True if saved successfully.
        """
        if not self.modified:
            return True

        if create_backup:
            # Create backup with .bak extension
            backup_path = self.config_path.with_suffix('.vdf.bak')
            try:
                shutil.copy2(self.config_path, backup_path)
            except OSError:
                pass  # Backup failed, but we proceed with saving

        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                vdf.dump(self.data, f, pretty=True)
            self.modified = False
            return True
        except OSError as e:
            # Re-use existing config save error from locales
            print(t('logs.config.save_error', error=e))
            return False

    def get_all_app_ids(self) -> List[str]:
        """Returns a list of all App IDs found in the config."""
        return list(self.apps.keys())

    def get_app_categories(self, app_id: str) -> List[str]:
        """
        Retrieves categories/tags for a specific app.

        Args:
            app_id (str): The Steam App ID.

        Returns:
            List[str]: List of category names.
        """
        app_data = self.apps.get(str(app_id), {})
        tags = app_data.get('tags', {})

        # Tags are stored as a dictionary {"0": "Tag", "1": "Tag"} or list
        if isinstance(tags, dict):
            return list(tags.values())
        return []

    def set_app_categories(self, app_id: str, categories: List[str]):
        """
        Overwrites categories for a specific app.

        Args:
            app_id (str): The Steam App ID.
            categories (List[str]): List of new category names.
        """
        if str(app_id) not in self.apps:
            self.apps[str(app_id)] = {}

        # Steam stores tags as Dict {"0": "Tag1", "1": "Tag2"}
        tags_dict = {str(i): cat for i, cat in enumerate(categories)}
        self.apps[str(app_id)]['tags'] = tags_dict
        self.modified = True

    def add_app_category(self, app_id: str, category: str):
        """Adds a single category to an app if not present."""
        categories = self.get_app_categories(app_id)
        if category not in categories:
            categories.append(category)
            self.set_app_categories(app_id, categories)

    def remove_app_category(self, app_id: str, category: str):
        """Removes a single category from an app."""
        categories = self.get_app_categories(app_id)
        if category in categories:
            categories.remove(category)
            self.set_app_categories(app_id, categories)

    def get_apps_in_category(self, category: str) -> List[str]:
        """Returns all App IDs belonging to a specific category."""
        apps = []
        for app_id in self.apps:
            if category in self.get_app_categories(app_id):
                apps.append(app_id)
        return apps

    def rename_category(self, old_name: str, new_name: str):
        """Renames a category across all apps."""
        for app_id in self.apps:
            categories = self.get_app_categories(app_id)
            if old_name in categories:
                # Replace old name with new name
                categories = [new_name if c == old_name else c for c in categories]
                self.set_app_categories(app_id, categories)

    def delete_category(self, category: str):
        """Removes a category from all apps."""
        for app_id in self.apps:
            self.remove_app_category(app_id, category)

    def get_app_data(self, app_id: str) -> Optional[Dict]:
        """Returns raw dictionary data for an app."""
        return self.apps.get(app_id)

    def set_app_data(self, app_id: str, data: Dict):
        """Sets raw dictionary data for an app."""
        self.apps[app_id] = data
        self.modified = True

    def get_uncategorized_apps(self) -> List[str]:
        """Returns App IDs that have no categories (or only 'favorite')."""
        uncategorized = []
        for app_id in self.apps:
            categories = self.get_app_categories(app_id)
            if not categories or categories == ['favorite']:
                uncategorized.append(app_id)
        return uncategorized

    # --- HIDDEN APP SUPPORT ---

    def get_hidden_apps(self) -> List[str]:
        """Returns list of all hidden App IDs."""
        hidden_apps = []
        for app_id, data in self.apps.items():
            # Steam stores Hidden as "1" (String) or 1 (Int)
            if 'Hidden' in data and str(data['Hidden']) == "1":
                hidden_apps.append(app_id)
        return hidden_apps

    def set_app_hidden(self, app_id: str, hidden: bool):
        """Sets or removes Hidden status for a game."""
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