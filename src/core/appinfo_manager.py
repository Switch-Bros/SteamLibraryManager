"""
AppInfo Manager - Manages Metadata Overrides & Loads Binary Steam Data
Speichern als: src/core/appinfo_manager.py
"""

import json
from pathlib import Path
from typing import Dict, Any, Optional
from src.utils.i18n import t
from src.utils import appinfo


class AppInfoManager:
    """Verwaltet manuelle Änderungen an Spiel-Metadaten und liest die binäre AppInfo"""

    def __init__(self, steam_path: Optional[Path] = None):
        self.data_dir = Path(__file__).parent.parent.parent / 'data'
        self.metadata_file = self.data_dir / 'custom_metadata.json'

        # Manuelle Änderungen (aus JSON)
        self.modifications: Dict[str, Dict] = {}

        # Steam Daten (aus binary vdf)
        self.steam_apps: Dict[str, Any] = {}
        self.appinfo_path: Optional[Path] = None

        if steam_path:
            self.appinfo_path = steam_path / 'appcache' / 'appinfo.vdf'

    def load_appinfo(self) -> Dict:
        """Lade Custom Overrides UND Binary AppInfo (für Namen)"""
        self.data_dir.mkdir(exist_ok=True)

        # 1. Custom Metadata laden
        if self.metadata_file.exists():
            try:
                with open(self.metadata_file, 'r', encoding='utf-8') as f:
                    self.modifications = json.load(f)
                print(t('logs.appinfo.loaded', count=len(self.modifications)))
            except (OSError, json.JSONDecodeError) as e:
                print(t('logs.appinfo.error', error=e))
                self.modifications = {}
        else:
            self.modifications = {}

        # 2. Binary AppInfo laden
        if self.appinfo_path and self.appinfo_path.exists():
            try:
                # WICHTIG: appinfo.vdf ist binär - mit 'rb' öffnen
                with open(self.appinfo_path, 'rb') as f:
                    data = appinfo.load(f)

                self.steam_apps = {}

                # Wir suchen nach dem 'common' Block, um Namen zu finden
                for app_id_str, content in data.items():
                    common = self._find_key_recursive(content, 'common')

                    if common and isinstance(common, dict):
                        name = common.get('name')
                        if name:
                            entry = {'name': name}
                            if 'developer' in common:
                                entry['developer'] = common['developer']
                            if 'publisher' in common:
                                entry['publisher'] = common['publisher']

                            self.steam_apps[app_id_str] = entry

                print(t('logs.appinfo.loaded_binary', count=len(self.steam_apps)))
            except (OSError, ValueError, KeyError, AttributeError) as e:
                print(t('logs.appinfo.binary_error', error=e))

        return self.modifications

    def _find_key_recursive(self, data: Any, target_key: str) -> Optional[Any]:
        """Hilfsfunktion: Sucht 'common' Block in verschachtelten Daten"""
        if not isinstance(data, dict):
            return None
        if target_key in data:
            return data[target_key]

        for val in data.values():
            if isinstance(val, dict):
                found = self._find_key_recursive(val, target_key)
                if found:
                    return found
        return None

    def get_app_metadata(self, app_id: str) -> Dict[str, Any]:
        """
        Gibt Metadaten für ein Spiel zurück.
        Reihenfolge: 1. Custom Override -> 2. Steam Binary Data -> 3. Leer
        """
        app_id = str(app_id)

        # Basis aus Steam Binary nehmen (falls vorhanden)
        base_meta = self.steam_apps.get(app_id, {}).copy()

        # Sicherstellen, dass Felder existieren (verhindert KeyError in UI)
        if 'name' not in base_meta: base_meta['name'] = ''
        if 'developer' not in base_meta: base_meta['developer'] = ''
        if 'publisher' not in base_meta: base_meta['publisher'] = ''

        # Override anwenden
        if app_id in self.modifications:
            base_meta.update(self.modifications[app_id])

        return base_meta

    def set_app_metadata(self, app_id: str, new_meta: Dict) -> bool:
        """Setze neue Metadaten für ein Spiel."""
        try:
            clean_meta = {k: v for k, v in new_meta.items() if v}

            if clean_meta:
                self.modifications[app_id] = clean_meta
            elif app_id in self.modifications:
                del self.modifications[app_id]

            return True
        except (ValueError, KeyError, TypeError) as e:
            print(t('logs.appinfo.set_error', app_id=app_id, error=e))
            return False

    def get_modification_count(self) -> int:
        return len(self.modifications)

    def save_appinfo(self) -> bool:
        """Speichere Änderungen in JSON"""
        try:
            with open(self.metadata_file, 'w', encoding='utf-8') as f:
                json.dump(self.modifications, f, indent=2)
            return True
        except OSError as e:
            print(t('logs.appinfo.save_error', error=e))
            return False

    def restore_modifications(self) -> int:
        """Löscht alle Änderungen (Reset)"""
        count = len(self.modifications)
        self.modifications = {}
        self.save_appinfo()
        return count