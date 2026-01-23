"""
AppInfo Manager - Direct Integration with SME Parser
Manages metadata modifications with full write support
Speichern als: src/core/appinfo_manager.py
"""

import json
from pathlib import Path
from typing import Dict, Any, Optional, List
from src.utils.i18n import t
from src.utils.appinfo import Appinfo, IncompatibleVDFError


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
        self.modifications: Dict[str, Dict] = {}  # {"app_id": {"original": {...}, "modified": {...}}}
        self.modified_apps: List[str] = []  # List of app IDs with modifications
        
        # Steam appinfo.vdf object
        self.appinfo: Optional[Appinfo] = None
        self.appinfo_path: Optional[Path] = None
        
        # Steam apps cache (for backwards compatibility)
        self.steam_apps: Dict[str, Any] = {}

        if steam_path:
            self.appinfo_path = steam_path / 'appcache' / 'appinfo.vdf'

    def load_appinfo(self, app_ids: Optional[List[str]] = None, load_all: bool = False) -> Dict:
        """
        Load appinfo.vdf using SME parser

        Args:
            app_ids: Specific app IDs to load (None = only modified apps)
            load_all: Load ALL apps (SLOW! Only use if necessary)

        Returns:
            Dict of modifications
        """
        self.data_dir.mkdir(exist_ok=True)

        # 1. Load saved modifications
        self._load_modifications_from_json()

        # 2. Load appinfo.vdf (binary)
        if self.appinfo_path and self.appinfo_path.exists():
            try:
                # Determine what to load
                if load_all:
                    # SLOW: Load everything
                    print(t('logs.appinfo.loading_all'))
                    self.appinfo = Appinfo(str(self.appinfo_path))

                elif app_ids:
                    # FIX: Prüfe ob app_ids nicht leer ist
                    if len(app_ids) == 0:
                        print(t('logs.appinfo.no_apps_to_load'))
                        return self.modifications

                    # Load specific apps
                    app_ids_int = [int(aid) if isinstance(aid, str) else aid for aid in app_ids]
                    self.appinfo = Appinfo(str(self.appinfo_path), choose_apps=True, apps=app_ids_int)

                elif self.modified_apps:
                    # FIX: Prüfe ob modified_apps nicht leer ist
                    if len(self.modified_apps) == 0:
                        print(t('logs.appinfo.no_apps_to_load'))
                        return self.modifications

                    # Load only modified apps
                    modified_int = [int(aid) if isinstance(aid, str) else aid for aid in self.modified_apps]
                    self.appinfo = Appinfo(str(self.appinfo_path), choose_apps=True, apps=modified_int)
                else:
                    # Nothing to load
                    print(t('logs.appinfo.no_apps_to_load'))
                    return self.modifications

                # Extract metadata to steam_apps cache (backwards compatibility)
                self._extract_to_cache()

                count = len(self.appinfo.parsedAppInfo) if self.appinfo else 0
                print(t('logs.appinfo.loaded_binary', count=count))

            except IncompatibleVDFError as e:
                print(t('logs.appinfo.incompatible_version', version=hex(e.vdf_version)))
            except Exception as e:
                print(f"Error loading binary appinfo: {e}")  # Bessere Fehlerausgabe
                import traceback
                traceback.print_exc()  # Zeigt wo genau der Fehler ist

        return self.modifications

    def _load_modifications_from_json(self):
        """Load saved metadata modifications"""
        if not self.metadata_file.exists():
            self.modifications = {}
            self.modified_apps = []
            return

        try:
            with open(self.metadata_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # Support both old and new formats
            self.modifications = {}
            self.modified_apps = []

            for app_id, mod_data in data.items():
                if isinstance(mod_data, dict):
                    # New format: {"original": {...}, "modified": {...}}
                    if 'original' in mod_data or 'modified' in mod_data:
                        self.modifications[app_id] = mod_data
                    else:
                        # Old format: Direct metadata
                        self.modifications[app_id] = {
                            'original': {},
                            'modified': mod_data
                        }
                    
                    self.modified_apps.append(app_id)

            print(t('logs.appinfo.loaded', count=len(self.modifications)))

        except (OSError, json.JSONDecodeError) as e:
            print(t('logs.appinfo.error', error=e))
            self.modifications = {}
            self.modified_apps = []

    def _extract_to_cache(self):
        """Extract metadata from appinfo to steam_apps cache"""
        if not self.appinfo:
            return
        
        self.steam_apps = {}
        
        for app_id, app_data in self.appinfo.parsedAppInfo.items():
            sections = app_data.get('sections', {})
            common = sections.get('common', {})
            
            if common:
                entry = {}
                
                if 'name' in common:
                    entry['name'] = common['name']
                if 'developer' in common:
                    entry['developer'] = common['developer']
                if 'publisher' in common:
                    entry['publisher'] = common['publisher']
                if 'type' in common:
                    entry['type'] = common['type']
                
                # Release date handling
                release_state = common.get('releasestate', '')
                if release_state:
                    entry['releasestate'] = release_state
                
                orig_release = common.get('original_release_date')
                if orig_release:
                    if isinstance(orig_release, int):
                        entry['release_date'] = str(orig_release)
                    elif isinstance(orig_release, dict):
                        entry['release_date'] = str(orig_release.get('date', ''))
                
                if entry:
                    self.steam_apps[str(app_id)] = entry

    def get_app_metadata(self, app_id: str) -> Dict[str, Any]:
        """
        Get metadata for a game
        Priority: Modified > appinfo.vdf > Empty
        """
        app_id = str(app_id)
        result = {}

        # 1. Get from appinfo.vdf cache
        if app_id in self.steam_apps:
            result = self.steam_apps[app_id].copy()
        elif self.appinfo:
            # Try to get from parsed appinfo
            app_id_int = int(app_id)
            if app_id_int in self.appinfo.parsedAppInfo:
                app_data = self.appinfo.parsedAppInfo[app_id_int]
                sections = app_data.get('sections', {})
                common = sections.get('common', {})
                
                result = {
                    'name': common.get('name', ''),
                    'type': common.get('type', ''),
                    'developer': common.get('developer', ''),
                    'publisher': common.get('publisher', ''),
                }

        # 2. Ensure fields exist
        if 'name' not in result: result['name'] = ''
        if 'developer' not in result: result['developer'] = ''
        if 'publisher' not in result: result['publisher'] = ''

        # 3. Apply modifications
        if app_id in self.modifications:
            modified = self.modifications[app_id].get('modified', {})
            result.update(modified)

        return result

    def set_app_metadata(self, app_id: str, new_meta: Dict) -> bool:
        """
        Set new metadata for a game
        Stores in JSON AND modifies appinfo object (if loaded)
        """
        app_id = str(app_id)

        try:
            # Track original values (if not already tracked)
            if app_id not in self.modifications:
                original = self.get_app_metadata(app_id)
                self.modifications[app_id] = {
                    'original': original.copy() if any(original.values()) else {},
                    'modified': {}
                }

            # Clean metadata (remove empty values)
            clean_meta = {k: v for k, v in new_meta.items() if v}

            if clean_meta:
                # Store modifications
                self.modifications[app_id]['modified'] = clean_meta

                # Add to modified list
                if app_id not in self.modified_apps:
                    self.modified_apps.append(app_id)

                # Update appinfo object (if loaded)
                if self.appinfo:
                    app_id_int = int(app_id)
                    if app_id_int in self.appinfo.parsedAppInfo:
                        sections = self.appinfo.parsedAppInfo[app_id_int]['sections']
                        
                        # Ensure 'common' block exists
                        if 'common' not in sections:
                            sections['common'] = {}
                        
                        common = sections['common']
                        
                        # Set values
                        for key, value in clean_meta.items():
                            common[key] = value
            else:
                # No changes - remove from tracking
                if app_id in self.modifications:
                    del self.modifications[app_id]
                if app_id in self.modified_apps:
                    self.modified_apps.remove(app_id)

            return True

        except Exception as e:
            print(t('logs.appinfo.set_error', app_id=app_id, error=e))
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
            print(t('logs.appinfo.save_error', error=e))
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
                BackupManager.create_rolling_backup(self.appinfo_path)

            # Write using SME's method
            modified_app_ids = [int(aid) for aid in self.modified_apps]
            self.appinfo.write_appinfo(modified_apps=modified_app_ids)

            print(t('logs.appinfo.saved_vdf'))
            return True

        except Exception as e:
            print(t('logs.appinfo.write_error', error=e))
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

        # Load appinfo for these apps
        self.load_appinfo(app_ids=app_ids)

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
