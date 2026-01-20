"""
localconfig.vdf Parser und Writer
Liest und schreibt Steam's localconfig.vdf Datei
Speichern als: src/core/localconfig_parser.py
"""

import vdf
import shutil
from pathlib import Path
from typing import Dict, List, Optional, Set
from datetime import datetime
from src.utils.i18n import t


class LocalConfigParser:
    """Parser für Steam's localconfig.vdf"""

    def __init__(self, config_path: Path):
        self.config_path = config_path
        self.data: Dict = {}
        self.apps: Dict = {}
        self.modified = False

    def load(self) -> bool:
        """Lade localconfig.vdf"""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                self.data = vdf.load(f)

            # Navigiere zur Apps-Sektion
            try:
                self.apps = self.data['UserLocalConfigStore']['Software']['Valve']['Steam']['Apps']
            except KeyError:
                print(t('logs.parser.apps_not_found'))
                self.apps = {}

            return True

        except FileNotFoundError:
            print(t('logs.parser.file_not_found', path=self.config_path))
            return False
        except Exception as e:
            print(t('logs.parser.load_error', error=e))
            return False

    def save(self, create_backup: bool = True) -> bool:
        """Speichere localconfig.vdf"""
        if not self.modified:
            print(t('logs.parser.no_changes'))
            return True

        try:
            # Backup erstellen
            if create_backup:
                self._create_backup()

            # Schreibe Datei
            with open(self.config_path, 'w', encoding='utf-8') as f:
                vdf.dump(self.data, f, pretty=True)

            self.modified = False
            print(t('logs.parser.saved'))
            return True

        except Exception as e:
            print(t('logs.parser.save_error', error=e))
            return False

    def _create_backup(self):
        """Erstelle Backup der localconfig.vdf"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_path = self.config_path.parent / f'localconfig_backup_{timestamp}.vdf'
        shutil.copy2(self.config_path, backup_path)
        print(t('logs.parser.backup_created', path=backup_path.name))

    def get_all_app_ids(self) -> List[str]:
        return list(self.apps.keys())

    def get_app_categories(self, app_id: str) -> List[str]:
        if app_id not in self.apps:
            return []

        app_data = self.apps[app_id]
        if 'tags' not in app_data:
            return []

        tags = app_data['tags']
        categories = []
        for key in sorted(tags.keys(), key=lambda x: int(x) if x.isdigit() else 0):
            categories.append(tags[key])

        return categories

    def set_app_categories(self, app_id: str, categories: List[str]):
        if app_id not in self.apps:
            self.apps[app_id] = {}

        if 'tags' in self.apps[app_id]:
            del self.apps[app_id]['tags']

        if categories:
            tags = {}
            for i, category in enumerate(categories):
                tags[str(i)] = category
            self.apps[app_id]['tags'] = tags

        self.modified = True

    def add_app_category(self, app_id: str, category: str):
        current_categories = self.get_app_categories(app_id)
        if category not in current_categories:
            current_categories.append(category)
            self.set_app_categories(app_id, current_categories)

    def remove_app_category(self, app_id: str, category: str):
        current_categories = self.get_app_categories(app_id)
        if category in current_categories:
            current_categories.remove(category)
            self.set_app_categories(app_id, current_categories)

    def get_all_categories(self) -> Set[str]:
        categories = set()
        for app_id in self.apps:
            app_categories = self.get_app_categories(app_id)
            categories.update(app_categories)
        return categories

    def get_apps_by_category(self, category: str) -> List[str]:
        apps = []
        for app_id in self.apps:
            if category in self.get_app_categories(app_id):
                apps.append(app_id)
        return apps

    def rename_category(self, old_name: str, new_name: str):
        for app_id in self.apps:
            categories = self.get_app_categories(app_id)
            if old_name in categories:
                categories = [new_name if c == old_name else c for c in categories]
                self.set_app_categories(app_id, categories)

    def delete_category(self, category: str):
        for app_id in self.apps:
            self.remove_app_category(app_id, category)

    def get_app_data(self, app_id: str) -> Optional[Dict]:
        return self.apps.get(app_id)

    def set_app_data(self, app_id: str, data: Dict):
        self.apps[app_id] = data
        self.modified = True

    def get_uncategorized_apps(self) -> List[str]:
        uncategorized = []
        for app_id in self.apps:
            categories = self.get_app_categories(app_id)
            if not categories or categories == ['favorite']:
                uncategorized.append(app_id)
        return uncategorized


if __name__ == "__main__":
    from pathlib import Path
    from src.utils.i18n import init_i18n

    init_i18n('en')

    # Test
    config_path = Path.home() / '.steam' / 'steam' / 'userdata' / '43925226' / 'config' / 'localconfig.vdf'
    parser = LocalConfigParser(config_path)

    if parser.load():
        print(f"✓ Loaded {len(parser.get_all_app_ids())} games")