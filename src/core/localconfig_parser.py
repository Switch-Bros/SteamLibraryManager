"""
localconfig.vdf Parser und Writer
Liest und schreibt Steam's localconfig.vdf Datei
"""

import vdf
import shutil
from pathlib import Path
from typing import Dict, List, Optional, Set
from datetime import datetime


class LocalConfigParser:
    """Parser für Steam's localconfig.vdf"""
    
    def __init__(self, config_path: Path):
        """
        Args:
            config_path: Pfad zur localconfig.vdf
        """
        self.config_path = config_path
        self.data: Dict = {}
        self.apps: Dict = {}
        self.modified = False
    
    def load(self) -> bool:
        """
        Lade localconfig.vdf
        
        Returns:
            True wenn erfolgreich
        """
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                self.data = vdf.load(f)
            
            # Navigiere zur Apps-Sektion
            try:
                self.apps = self.data['UserLocalConfigStore']['Software']['Valve']['Steam']['Apps']
            except KeyError:
                print("Warning: Apps section not found in localconfig.vdf")
                self.apps = {}
            
            return True
            
        except FileNotFoundError:
            print(f"Error: localconfig.vdf not found at {self.config_path}")
            return False
        except Exception as e:
            print(f"Error loading localconfig.vdf: {e}")
            return False
    
    def save(self, create_backup: bool = True) -> bool:
        """
        Speichere localconfig.vdf
        
        Args:
            create_backup: Backup vor dem Speichern erstellen
            
        Returns:
            True wenn erfolgreich
        """
        if not self.modified:
            print("No changes to save")
            return True
        
        try:
            # Backup erstellen
            if create_backup:
                self._create_backup()
            
            # Schreibe Datei
            with open(self.config_path, 'w', encoding='utf-8') as f:
                vdf.dump(self.data, f, pretty=True)
            
            self.modified = False
            print(f"✓ Saved localconfig.vdf")
            return True
            
        except Exception as e:
            print(f"Error saving localconfig.vdf: {e}")
            return False
    
    def _create_backup(self):
        """Erstelle Backup der localconfig.vdf"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_path = self.config_path.parent / f'localconfig_backup_{timestamp}.vdf'
        shutil.copy2(self.config_path, backup_path)
        print(f"✓ Backup created: {backup_path.name}")
    
    def get_all_app_ids(self) -> List[str]:
        """
        Hole alle App IDs
        
        Returns:
            Liste von App IDs (als Strings)
        """
        return list(self.apps.keys())
    
    def get_app_categories(self, app_id: str) -> List[str]:
        """
        Hole Kategorien für ein Spiel
        
        Args:
            app_id: Steam App ID
            
        Returns:
            Liste von Kategorien
        """
        if app_id not in self.apps:
            return []
        
        app_data = self.apps[app_id]
        
        if 'tags' not in app_data:
            return []
        
        tags = app_data['tags']
        
        # Tags sind als Dict gespeichert: {"0": "RPG", "1": "Action", ...}
        categories = []
        for key in sorted(tags.keys(), key=lambda x: int(x) if x.isdigit() else 0):
            categories.append(tags[key])
        
        return categories
    
    def set_app_categories(self, app_id: str, categories: List[str]):
        """
        Setze Kategorien für ein Spiel
        
        Args:
            app_id: Steam App ID
            categories: Liste von Kategorien
        """
        if app_id not in self.apps:
            self.apps[app_id] = {}
        
        # Lösche alte tags
        if 'tags' in self.apps[app_id]:
            del self.apps[app_id]['tags']
        
        # Setze neue tags
        if categories:
            tags = {}
            for i, category in enumerate(categories):
                tags[str(i)] = category
            self.apps[app_id]['tags'] = tags
        
        self.modified = True
    
    def add_app_category(self, app_id: str, category: str):
        """
        Füge Kategorie zu einem Spiel hinzu
        
        Args:
            app_id: Steam App ID
            category: Kategorie-Name
        """
        current_categories = self.get_app_categories(app_id)
        
        if category not in current_categories:
            current_categories.append(category)
            self.set_app_categories(app_id, current_categories)
    
    def remove_app_category(self, app_id: str, category: str):
        """
        Entferne Kategorie von einem Spiel
        
        Args:
            app_id: Steam App ID
            category: Kategorie-Name
        """
        current_categories = self.get_app_categories(app_id)
        
        if category in current_categories:
            current_categories.remove(category)
            self.set_app_categories(app_id, current_categories)
    
    def get_all_categories(self) -> Set[str]:
        """
        Hole alle verwendeten Kategorien
        
        Returns:
            Set von Kategorie-Namen
        """
        categories = set()
        
        for app_id in self.apps:
            app_categories = self.get_app_categories(app_id)
            categories.update(app_categories)
        
        return categories
    
    def get_apps_by_category(self, category: str) -> List[str]:
        """
        Hole alle Spiele in einer Kategorie
        
        Args:
            category: Kategorie-Name
            
        Returns:
            Liste von App IDs
        """
        apps = []
        
        for app_id in self.apps:
            if category in self.get_app_categories(app_id):
                apps.append(app_id)
        
        return apps
    
    def rename_category(self, old_name: str, new_name: str):
        """
        Benenne Kategorie um (für alle Spiele)
        
        Args:
            old_name: Alter Name
            new_name: Neuer Name
        """
        for app_id in self.apps:
            categories = self.get_app_categories(app_id)
            if old_name in categories:
                categories = [new_name if c == old_name else c for c in categories]
                self.set_app_categories(app_id, categories)
    
    def delete_category(self, category: str):
        """
        Lösche Kategorie (von allen Spielen)
        
        Args:
            category: Kategorie-Name
        """
        for app_id in self.apps:
            self.remove_app_category(app_id, category)
    
    def get_app_data(self, app_id: str) -> Optional[Dict]:
        """
        Hole komplette Daten für ein Spiel
        
        Args:
            app_id: Steam App ID
            
        Returns:
            Dict mit Spiel-Daten oder None
        """
        return self.apps.get(app_id)
    
    def set_app_data(self, app_id: str, data: Dict):
        """
        Setze komplette Daten für ein Spiel
        
        Args:
            app_id: Steam App ID
            data: Dict mit Spiel-Daten
        """
        self.apps[app_id] = data
        self.modified = True
    
    def get_uncategorized_apps(self) -> List[str]:
        """
        Hole alle Spiele ohne Kategorien
        
        Returns:
            Liste von App IDs
        """
        uncategorized = []
        
        for app_id in self.apps:
            categories = self.get_app_categories(app_id)
            if not categories or categories == ['favorite']:
                # "favorite" alleine zählt nicht als kategorisiert
                uncategorized.append(app_id)
        
        return uncategorized


# Beispiel-Nutzung
if __name__ == "__main__":
    from pathlib import Path
    
    # Test
    config_path = Path.home() / '.steam' / 'steam' / 'userdata' / '43925226' / 'config' / 'localconfig.vdf'
    
    parser = LocalConfigParser(config_path)
    
    if parser.load():
        print(f"✓ Loaded {len(parser.get_all_app_ids())} games")
        
        # Zeige alle Kategorien
        categories = parser.get_all_categories()
        print(f"\nFound {len(categories)} categories:")
        for cat in sorted(categories):
            apps_in_cat = len(parser.get_apps_by_category(cat))
            print(f"  • {cat}: {apps_in_cat} games")
        
        # Zeige unkategorisierte Spiele
        uncategorized = parser.get_uncategorized_apps()
        print(f"\nUncategorized: {len(uncategorized)} games")
