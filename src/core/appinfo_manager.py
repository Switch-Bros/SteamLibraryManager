# src/core/appinfo_manager.py

"""
Manages Steam app metadata modifications and binary appinfo.vdf operations.

This module provides functionality to read, modify, and write Steam's appinfo.vdf
file, which contains metadata for all Steam applications. It tracks user modifications
separately and supports restoring them after Steam updates the file.
"""

import json
from pathlib import Path
from typing import Dict, Any, Optional, List
from src.utils.i18n import t
from src.utils.appinfo import AppInfo, IncompatibleVersionError


class AppInfoManager:
    """
    Manages Steam app metadata modifications with VDF write support.

    This class handles reading Steam's binary appinfo.vdf file, tracking user
    modifications to app metadata (like developer, publisher, release date),
    and writing those changes back to the VDF file with correct checksums.
    """

    def __init__(self, steam_path: Optional[Path] = None):
        """
        Initializes the AppInfoManager.

        Args:
            steam_path (Optional[Path]): Path to the Steam installation directory.
                                         If provided, appinfo.vdf will be loaded from
                                         <steam_path>/appcache/appinfo.vdf.
        """
        self.data_dir = Path(__file__).parent.parent.parent / 'data'
        self.metadata_file = self.data_dir / 'custom_metadata.json'

        # Tracking dictionaries
        self.modifications: Dict[str, Dict] = {}
        self.modified_apps: List[str] = []

        # Steam appinfo.vdf object
        self.appinfo: Optional[AppInfo] = None
        self.appinfo_path: Optional[Path] = None

        # Steam apps cache (for backwards compatibility)
        self.steam_apps: Dict[int, Dict] = {}

        if steam_path:
            self.appinfo_path = steam_path / 'appcache' / 'appinfo.vdf'

    def load_appinfo(self, _app_ids: Optional[List[str]] = None, _load_all: bool = False) -> Dict:
        """
        Loads the binary appinfo.vdf and previously saved modifications.

        This method reads the Steam appinfo.vdf file using the appinfo_v2 parser
        and loads any custom metadata modifications from the JSON file.

        Args:
            _app_ids (Optional[List[str]]): Reserved for future use (currently ignored).
            _load_all (bool): Reserved for future use (currently ignored).

        Returns:
            Dict: A dictionary of all tracked modifications, keyed by app_id.
        """
        self.data_dir.mkdir(exist_ok=True)

        # 1. Load saved modifications
        self._load_modifications_from_json()

        # 2. Load binary appinfo.vdf
        if self.appinfo_path and self.appinfo_path.exists():
            try:
                # Load appinfo.vdf
                self.appinfo = AppInfo(path=str(self.appinfo_path))

                # Update steam_apps cache
                self.steam_apps = self.appinfo.apps

                count = len(self.appinfo.apps)
                print(t('logs.appinfo.loaded_binary', count=count))

            except IncompatibleVersionError as e:
                print(t('logs.appinfo.incompatible_version', version=hex(e.version)))
            except Exception as e:
                print(t('logs.appinfo.binary_error', error=str(e)))
                import traceback
                traceback.print_exc()

        return self.modifications

    def _load_modifications_from_json(self):
        """
        Loads saved metadata modifications from the JSON file.

        Supports both old (direct metadata) and new (original + modified) formats.
        """
        if not self.metadata_file.exists():
            self.modifications = {}
            self.modified_apps = []
            return

        try:
            with open(self.metadata_file, 'r', encoding='utf-8') as f:
                file_data = json.load(f)

            # Support both old and new formats
            self.modifications = {}
            self.modified_apps = []

            for app_id_str, mod_data in file_data.items():
                if isinstance(mod_data, dict):
                    # New format: {"original": {...}, "modified": {...}}
                    if 'original' in mod_data or 'modified' in mod_data:
                        self.modifications[app_id_str] = mod_data
                    else:
                        # Old format: Direct metadata
                        self.modifications[app_id_str] = {
                            'original': {},
                            'modified': mod_data
                        }

                    self.modified_apps.append(app_id_str)

            print(t('logs.appinfo.loaded', count=len(self.modifications)))

        except (OSError, json.JSONDecodeError) as e:
            print(t('logs.appinfo.error', error=str(e)))
            self.modifications = {}
            self.modified_apps = []

    @staticmethod
    def _find_common_section(data: Dict) -> Dict:
        """
        Recursively searches for the 'common' section in VDF data.

        Steam's appinfo.vdf structure can vary. This method tries multiple
        paths to locate the 'common' section that contains app metadata.

        Args:
            data (Dict): The VDF data dictionary to search.

        Returns:
            Dict: The 'common' section dictionary, or an empty dict if not found.
        """
        # 1. Direct hit
        if 'common' in data:
            return data['common']

        # 2. Nested in appinfo
        if 'appinfo' in data and 'common' in data['appinfo']:
            return data['appinfo']['common']

        # 3. Recursive search (limited depth)
        for key, value in data.items():
            if isinstance(value, dict):
                if 'common' in value:
                    return value['common']
                # Search only one level deeper to save performance
                if 'appinfo' in value and 'common' in value['appinfo']:
                    return value['appinfo']['common']

        return {}

    def get_app_metadata(self, app_id: str) -> Dict[str, Any]:
        """
        Retrieves app metadata with user modifications applied.

        This method first reads metadata from the binary appinfo.vdf, then
        applies any custom modifications tracked in the JSON file. It supports
        both the old (direct fields) and new (associations block) formats for
        developer and publisher information.

        Args:
            app_id (str): The Steam app ID as a string.

        Returns:
            Dict[str, Any]: A dictionary containing metadata fields like 'name',
                           'developer', 'publisher', 'release_date', etc.
        """
        result = {}

        # 1. Get from binary appinfo
        if self.appinfo and int(app_id) in self.appinfo.apps:
            app_data_full = self.appinfo.apps[int(app_id)]
            vdf_data = app_data_full.get('data', {})

            # Find common section - use helper method!
            common = self._find_common_section(vdf_data)

            if common:
                # Name & Type
                result['name'] = common.get('name', '')
                result['type'] = common.get('type', '')

                # =============================================
                # DEVELOPER & PUBLISHER - ASSOCIATIONS FIRST!
                # =============================================
                devs = []
                pubs = []

                # A) TRY 'associations' FIRST (new format)
                if 'associations' in common:
                    assoc = common['associations']

                    # associations is a Dict with index as Key ("0", "1", ...)
                    for entry in assoc.values():
                        if isinstance(entry, dict):
                            entry_type = entry.get('type', '')
                            entry_name = entry.get('name', '')

                            if entry_type == 'developer' and entry_name:
                                devs.append(entry_name)
                            elif entry_type == 'publisher' and entry_name:
                                pubs.append(entry_name)

                # B) FALLBACK: Direct fields (old format)
                if not devs:
                    dev_direct = common.get('developer', '')
                    if dev_direct:
                        devs = [dev_direct] if isinstance(dev_direct, str) else list(dev_direct)

                if not pubs:
                    pub_direct = common.get('publisher', '')
                    if pub_direct:
                        pubs = [pub_direct] if isinstance(pub_direct, str) else list(pub_direct)

                # Set results
                result['developer'] = ", ".join(devs) if devs else ''
                result['publisher'] = ", ".join(pubs) if pubs else ''

                # =============================================
                # RELEASE DATE
                # =============================================
                # Try multiple keys
                if 'steam_release_date' in common:
                    result['release_date'] = common.get('steam_release_date', '')
                elif 'release_date' in common:
                    result['release_date'] = common.get('release_date', '')
                else:
                    result['release_date'] = ''

                # =============================================
                # REVIEW PERCENTAGE & METACRITIC SCORE
                # =============================================
                # Extract review percentage (0-100)
                if 'review_percentage' in common:
                    result['review_percentage'] = common.get('review_percentage', 0)

                # Extract metacritic score (0-100)
                if 'metacritic_score' in common:
                    result['metacritic_score'] = common.get('metacritic_score', 0)

        # 2. Apply modifications (Custom Overrides)
        if app_id in self.modifications:
            modified = self.modifications[app_id].get('modified', {})
            result.update(modified)

        return result

    def set_app_metadata(self, app_id: str, metadata: Dict[str, Any]) -> bool:
        """
        Sets custom metadata for an app and tracks the modification.

        This method stores the original values (if not already stored) and
        updates the modified values. If the binary appinfo.vdf is loaded,
        the changes are also applied in-memory.

        Args:
            app_id (str): The Steam app ID as a string.
            metadata (Dict[str, Any]): A dictionary of metadata fields to update
                                       (e.g., {'developer': 'New Dev', 'publisher': 'New Pub'}).

        Returns:
            bool: True if the operation succeeded, False otherwise.
        """
        try:
            # Get original values
            if app_id not in self.modifications:
                original = self.get_app_metadata(app_id)
                self.modifications[app_id] = {
                    'original': original.copy(),
                    'modified': {}
                }

            # Update modified values
            self.modifications[app_id]['modified'].update(metadata)

            # Track as modified
            if app_id not in self.modified_apps:
                self.modified_apps.append(app_id)

            # Apply to binary appinfo if loaded
            if self.appinfo and int(app_id) in self.appinfo.apps:
                self.appinfo.update_app_metadata(int(app_id), metadata)

            return True

        except Exception as e:
            print(t('logs.appinfo.set_error', app_id=app_id, error=str(e)))
            return False

    def save_appinfo(self) -> bool:
        """
        Saves all tracked modifications to the JSON file.

        Returns:
            bool: True if the save operation succeeded, False otherwise.
        """
        try:
            self.data_dir.mkdir(exist_ok=True, parents=True)
            with open(self.metadata_file, 'w', encoding='utf-8') as f:
                json.dump(self.modifications, f, indent=2)
            print(t('logs.appinfo.saved_mods', count=len(self.modifications)))
            return True
        except OSError as e:
            print(t('logs.appinfo.error', error=str(e)))
            return False

    def write_to_vdf(self, backup: bool = True) -> bool:
        """
        Writes all in-memory modifications back to the binary appinfo.vdf file.

        This method uses the appinfo_v2 library to write the VDF file with
        correct checksums. A backup is created by default before writing.

        Args:
            backup (bool): Whether to create a rolling backup before writing.

        Returns:
            bool: True if the write operation succeeded, False otherwise.
        """
        if not self.appinfo:
            print(t('logs.appinfo.not_loaded'))
            return False

        try:
            # Create backup
            if backup:
                from src.core.backup_manager import BackupManager
                backup_manager = BackupManager()
                backup_path = backup_manager.create_rolling_backup(self.appinfo_path)
                if backup_path:
                    print(t('logs.appinfo.backup_created', path=backup_path))
                else:
                    print(t('logs.appinfo.backup_failed', error=t('common.unknown')))

            # Write using appinfo_v2's method
            success = self.appinfo.write()
            if success:
                print(t('logs.appinfo.saved_vdf'))
            return success

        except Exception as e:
            print(t('logs.appinfo.write_error', error=str(e)))
            import traceback
            traceback.print_exc()
            return False

    def restore_modifications(self, app_ids: Optional[List[str]] = None) -> int:
        """
        Restores saved modifications to the binary appinfo.vdf.

        This is useful after Steam updates the appinfo.vdf file and overwrites
        custom metadata. The method re-applies all tracked modifications.

        Args:
            app_ids (Optional[List[str]]): A list of app IDs to restore. If None,
                                          all tracked modifications are restored.

        Returns:
            int: The number of apps successfully restored.
        """
        if not app_ids:
            app_ids = list(self.modifications.keys())

        if not app_ids:
            return 0

        # Load appinfo
        self.load_appinfo()

        restored = 0
        for app_id in app_ids:
            if app_id in self.modifications:
                modified = self.modifications[app_id].get('modified', {})
                if modified and self.set_app_metadata(app_id, modified):
                    restored += 1

        if restored > 0:
            self.write_to_vdf()
            print(t('logs.appinfo.restored', count=restored))

        return restored

    def get_modification_count(self) -> int:
        """
        Returns the number of apps with tracked modifications.

        Returns:
            int: The count of modified apps.
        """
        return len(self.modifications)

    def clear_all_modifications(self) -> int:
        """
        Clears all tracked modifications and saves the empty state.

        Returns:
            int: The number of modifications that were cleared.
        """
        count = len(self.modifications)
        self.modifications = {}
        self.modified_apps = []
        self.save_appinfo()
        return count
