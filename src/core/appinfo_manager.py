"""
AppInfo Manager - Verwaltet appinfo.vdf Metadaten

Speichern als: src/core/appinfo_manager.py
"""

import json
import shutil
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime


class AppInfoManager:
    """Verwaltet Steam's appinfo.vdf Datei"""
    
    def __init__(self, steam_path: Path):
        self.steam_path = steam_path
        self.appinfo_path = steam_path / 'appcache' / 'appinfo.vdf'
        self.backup_dir = steam_path / 'appcache' / 'metadata_backups'
        self.changes_file = steam_path / 'appcache' / 'metadata_changes.json'
        self.backup_dir.mkdir(exist_ok=True)
        self.modifications: Dict[str, Dict] = {}
        self._load_modifications()
    
    def _load_modifications(self):
        if self.changes_file.exists():
            try:
                with open(self.changes_file, 'r', encoding='utf-8') as f:
                    self.modifications = json.load(f)
                print(f"✓ Loaded {len(self.modifications)} saved modifications")
            except Exception as e:
                print(f"Error loading modifications: {e}")
                self.modifications = {}
    
    def _save_modifications(self):
        try:
            with open(self.changes_file, 'w', encoding='utf-8') as f:
                json.dump(self.modifications, f, indent=2)
            print(f"✓ Saved {len(self.modifications)} modifications")
        except Exception as e:
            print(f"Error saving modifications: {e}")
    
    def load_appinfo(self) -> Dict:
        if not self.appinfo_path.exists():
            print(f"Error: appinfo.vdf not found at {self.appinfo_path}")
            return {}
        try:
            from src.utils.vdf_wrapper import AppInfoVDF
            data = AppInfoVDF.load(self.appinfo_path)
            print(f"✓ Loaded appinfo.vdf with {len(data)} apps")
            return data
        except Exception as e:
            print(f"Error loading appinfo.vdf: {e}")
            import traceback
            traceback.print_exc()
            return {}
    
    def save_appinfo(self, data: Dict, create_backup: bool = True) -> bool:
        if create_backup:
            self._create_backup()
        try:
            from src.utils.vdf_wrapper import AppInfoVDF
            if AppInfoVDF.dump(data, self.appinfo_path):
                print(f"✓ Saved appinfo.vdf")
                return True
            else:
                return False
        except Exception as e:
            print(f"Error saving appinfo.vdf: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def _create_backup(self):
        if not self.appinfo_path.exists():
            return
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_path = self.backup_dir / f'appinfo_backup_{timestamp}.vdf'
        try:
            shutil.copy2(self.appinfo_path, backup_path)
            print(f"✓ Backup created: {backup_path.name}")
            self._cleanup_old_backups()
        except Exception as e:
            print(f"Error creating backup: {e}")
    
    def _cleanup_old_backups(self):
        backups = sorted(self.backup_dir.glob('appinfo_backup_*.vdf'))
        if len(backups) > 10:
            for old_backup in backups[:-10]:
                try:
                    old_backup.unlink()
                    print(f"  Removed old backup: {old_backup.name}")
                except Exception as e:
                    print(f"  Error removing {old_backup.name}: {e}")
    
    def get_app_metadata(self, app_id: str, data: Dict) -> Optional[Dict]:
        if app_id not in data:
            return None
        app = data[app_id]
        common = app.get('appinfo', {}).get('common', {})
        return {
            'name': common.get('name', ''),
            'developer': common.get('developer', ''),
            'publisher': common.get('publisher', ''),
            'release_date': common.get('steam_release_date', ''),
            'sort_as': common.get('sort_as', ''),
            'app_id': app_id,
        }
    
    def set_app_metadata(self, app_id: str, data: Dict, metadata: Dict) -> bool:
        if app_id not in data:
            print(f"App {app_id} not found in appinfo")
            return False
        try:
            if 'appinfo' not in data[app_id]:
                data[app_id]['appinfo'] = {}
            if 'common' not in data[app_id]['appinfo']:
                data[app_id]['appinfo']['common'] = {}
            
            common = data[app_id]['appinfo']['common']
            original = {
                'name': common.get('name'),
                'developer': common.get('developer'),
                'publisher': common.get('publisher'),
                'release_date': common.get('steam_release_date'),
                'sort_as': common.get('sort_as'),
            }
            
            if 'name' in metadata and metadata['name']:
                common['name'] = metadata['name']
                if 'sort_as' not in metadata or not metadata['sort_as']:
                    common['sort_as'] = metadata['name']
            
            if 'developer' in metadata and metadata['developer']:
                common['developer'] = metadata['developer']
            
            if 'publisher' in metadata and metadata['publisher']:
                common['publisher'] = metadata['publisher']
            
            if 'release_date' in metadata and metadata['release_date']:
                common['steam_release_date'] = metadata['release_date']
            
            if 'sort_as' in metadata and metadata['sort_as']:
                common['sort_as'] = metadata['sort_as']
            
            self.modifications[app_id] = {
                'original': original,
                'modified': metadata,
                'timestamp': datetime.now().isoformat()
            }
            self._save_modifications()
            return True
        except Exception as e:
            print(f"Error setting metadata for {app_id}: {e}")
            return False
    
    def bulk_set_metadata(self, app_ids: List[str], data: Dict, metadata: Dict) -> int:
        success_count = 0
        for app_id in app_ids:
            if self.set_app_metadata(app_id, data, metadata):
                success_count += 1
        return success_count
    
    def restore_modifications(self, data: Dict) -> int:
        if not self.modifications:
            print("No modifications to restore")
            return 0
        print(f"Restoring {len(self.modifications)} modifications...")
        restored = 0
        for app_id, mod in self.modifications.items():
            if self.set_app_metadata(app_id, data, mod['modified']):
                restored += 1
        print(f"✓ Restored {restored} modifications")
        return restored
    
    def revert_app(self, app_id: str, data: Dict) -> bool:
        if app_id not in self.modifications:
            print(f"No modifications found for app {app_id}")
            return False
        original = self.modifications[app_id]['original']
        if self.set_app_metadata(app_id, data, original):
            del self.modifications[app_id]
            self._save_modifications()
            print(f"✓ Reverted app {app_id} to original")
            return True
        return False
    
    def get_modification_count(self) -> int:
        return len(self.modifications)
    
    def get_modified_apps(self) -> List[str]:
        return list(self.modifications.keys())
    
    def clear_all_modifications(self):
        self.modifications = {}
        self._save_modifications()
        print("✓ Cleared all modification records")
