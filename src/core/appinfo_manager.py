"""
AppInfo Manager - Direct Integration with appinfo_v2 Parser
Manages metadata modifications with full write support
Speichern als: src/core/appinfo_manager.py
"""

import json
from pathlib import Path
from typing import Dict, Any, Optional, List
from src.utils.i18n import t
from src.utils.appinfo import AppInfo, IncompatibleVersionError


class AppInfoManager:
    """
    Manages Steam app metadata modifications
    - Tracks original and modified values
    - Supports writing to appinfo.vdf with correct checksums
    - Provides restore functionality
    """

    def __init__(self, steam_path: Optional[Path] = None):
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
        Load appinfo.vdf using appinfo_v2 parser

        Args:
            _app_ids: [UNUSED] Kept for API compatibility
            _load_all: [UNUSED] Kept for API compatibility

        Returns:
            Dict of modifications
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
        """Load saved metadata modifications"""
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

    def get_app_metadata(self, app_id: str) -> Dict[str, Any]:
        """
        Get app metadata (with modifications applied)

        Returns:
            Dict with current metadata
        """
        result = {}

        # 1. Get from binary appinfo
        if self.appinfo and int(app_id) in self.appinfo.apps:
            app_data_dict = self.appinfo.apps[int(app_id)]
            sections = app_data_dict.get('data', {})
            common_section = sections.get('common', {})

            result['name'] = common_section.get('name', '')
            result['type'] = common_section.get('type', '')
            result['developer'] = common_section.get('developer', '')
            result['publisher'] = common_section.get('publisher', '')
            result['release_date'] = common_section.get('steam_release_date', '')

        # 2. Apply modifications
        if app_id in self.modifications:
            modified = self.modifications[app_id].get('modified', {})
            result.update(modified)

        return result

    def set_app_metadata(self, app_id: str, metadata: Dict[str, Any]) -> bool:
        """
        Set app metadata (tracks original + modified)

        Args:
            app_id: Steam App ID
            metadata: New metadata values

        Returns:
            bool: Success
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
        """Save modifications to JSON"""
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
        Write modifications back to appinfo.vdf
        CRITICAL: Uses correct SHA-1 checksum algorithm

        Args:
            backup: Create backup before writing

        Returns:
            bool: Success
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
                    print(t('logs.appinfo.backup_failed', error=t('errors.unknown')))

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
        Restore saved modifications to appinfo.vdf
        (In case Steam overwrote them)

        Args:
            app_ids: Specific app IDs to restore (None = all)

        Returns:
            int: Number of apps restored
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

        # Write back to appinfo.vdf
        if restored > 0:
            self.write_to_vdf()
            print(t('logs.appinfo.restoredvdf', count=restored))

        return restored

    def get_modification_count(self) -> int:
        """Get number of modified apps"""
        return len(self.modifications)

    def clear_all_modifications(self) -> int:
        """
        Clear ALL modifications (DANGEROUS!)

        Returns:
            int: Number of modifications cleared
        """
        count = len(self.modifications)
        self.modifications = {}
        self.modified_apps = []
        self.save_appinfo()
        return count