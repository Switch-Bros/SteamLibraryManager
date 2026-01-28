"""
AppInfo Manager - Associations Support Edition
Manages Steam app metadata modifications, tracks changes, and supports writing to appinfo.vdf.
"""

import json
from pathlib import Path
from typing import Dict, Any, Optional, List
from src.utils.i18n import t
from src.utils.appinfo import AppInfo, IncompatibleVersionError


class AppInfoManager:
    """
    Manages Steam app metadata modifications.
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
        """Load appinfo.vdf using appinfo_v2 parser."""
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
        """Load saved metadata modifications."""
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
        Recursive search for the 'common' section.
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
        Get app metadata (with modifications applied).
        Supports 'associations' block for Developers/Publishers.
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

        # 2. Apply modifications (Custom Overrides)
        if app_id in self.modifications:
            modified = self.modifications[app_id].get('modified', {})
            result.update(modified)

        return result

    def set_app_metadata(self, app_id: str, metadata: Dict[str, Any]) -> bool:
        """Set app metadata."""
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
        """Save modifications to JSON."""
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
        """Write modifications back to appinfo.vdf."""
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
                    # 'errors.unknown' does not exist in locale, using 'common.unknown'
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
        """Restore saved modifications to appinfo.vdf."""
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
            # Changed 'restoredvdf' to 'restored' to match locale key
            print(t('logs.appinfo.restored', count=restored))

        return restored

    def get_modification_count(self) -> int:
        return len(self.modifications)

    def clear_all_modifications(self) -> int:
        count = len(self.modifications)
        self.modifications = {}
        self.modified_apps = []
        self.save_appinfo()
        return count