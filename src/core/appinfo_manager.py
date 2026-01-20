"""
AppInfo Manager - Verwaltet Metadaten-Overrides (Custom Metadata)
Speichern als: src/core/appinfo_manager.py
"""

import json
from pathlib import Path
from typing import Dict, Optional, Any
from src.utils.i18n import t


class AppInfoManager:
    """Verwaltet manuelle Änderungen an Spiel-Metadaten"""

    def __init__(self, steam_path: Path = None):
        self.data_dir = Path(__file__).parent.parent.parent / 'data'
        self.metadata_file = self.data_dir / 'custom_metadata.json'
        self.modifications: Dict[str, Dict] = {}

    def load_appinfo(self) -> Dict:
        """Lade die gespeicherten Overrides"""
        self.data_dir.mkdir(exist_ok=True)

        if self.metadata_file.exists():
            try:
                with open(self.metadata_file, 'r', encoding='utf-8') as f:
                    self.modifications = json.load(f)
                print(t('logs.appinfo.loaded', count=len(self.modifications)))
            except Exception as e:
                print(t('logs.appinfo.error', error=e))
                self.modifications = {}
        else:
            self.modifications = {}

        return self.modifications

    def save_appinfo(self, data: Dict = None) -> bool:
        """Speichere Änderungen in JSON"""
        # data Argument ist hier nur noch für Kompatibilität, wir nutzen self.modifications
        if data is not None:
            self.modifications = data

        try:
            with open(self.metadata_file, 'w', encoding='utf-8') as f:
                json.dump(self.modifications, f, indent=2, ensure_ascii=False)
            print(t('logs.appinfo.saved_mods', count=len(self.modifications)))
            return True
        except Exception as e:
            print(t('logs.appinfo.save_error', error=e))
            return False

    def get_app_metadata(self, app_id: str) -> Dict:
        """
        Gibt die Metadaten für ein Spiel zurück.
        FIX: Kein 'data' Argument mehr nötig!
        """
        # Vorlage
        base_meta = {
            'name': '',
            'sort_as': '',
            'developer': '',
            'publisher': '',
            'release_date': ''
        }

        # Wenn wir schon Änderungen haben, lade diese
        if app_id in self.modifications:
            base_meta.update(self.modifications[app_id])

        return base_meta

    def set_app_metadata(self, app_id: str, new_meta: Dict) -> bool:
        """
        Setze neue Metadaten für ein Spiel.
        FIX: Kein 'current_data' Argument mehr nötig!
        """
        try:
            # Wir speichern nur die Felder, die wirklich gesetzt sind
            clean_meta = {k: v for k, v in new_meta.items() if v}

            if clean_meta:
                self.modifications[app_id] = clean_meta
            elif app_id in self.modifications:
                # Wenn alles leer ist, löschen wir den Eintrag (Reset)
                del self.modifications[app_id]

            return True
        except Exception as e:
            print(t('logs.appinfo.set_error', app_id=app_id, error=e))
            return False

    def get_modification_count(self) -> int:
        return len(self.modifications)

    def restore_modifications(self, current_data: Dict = None) -> int:
        """Löscht alle Änderungen (Reset)"""
        count = len(self.modifications)
        self.modifications = {}
        return count