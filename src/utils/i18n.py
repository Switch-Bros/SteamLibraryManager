"""
Internationalization (i18n) system
Loads translation files dynamically from resources/i18n/{locale}/*.json
"""
import json
from pathlib import Path
from typing import Optional, Dict, Any


class I18n:
    """
    Core internationalization class.
    Scans the folder resources/i18n/{locale}/ and loads all JSON files found there.
    """

    def __init__(self, locale: str = 'en'):
        """
        Initialize I18n with a specific locale code.
        The code is used to find the corresponding directory in resources/i18n/.
        """
        self.locale = locale
        self.translations: Dict[str, Any] = {}
        self.fallback_translations: Dict[str, Any] = {}

        # Path: PROJECT/resources/i18n
        current_file = Path(__file__).resolve()
        project_root = current_file.parent.parent.parent
        self.i18n_root = project_root / 'resources' / 'i18n'

        self._load_translations()

    def _load_translations(self):
        """
        Loads translations.
        1. Loads English fallback from resources/i18n/en/*.json
        2. Loads Target Locale dynamically from resources/i18n/{self.locale}/*.json
        """
        # 1. Load Fallback (English)
        self.fallback_translations = self._load_locale_directory('en')

        # 2. Load Target Locale (if different from English)
        if self.locale != 'en':
            # This uses the variable 'self.locale' (e.g. 'it', 'de', 'es')
            # No hardcoded languages here!
            target_data = self._load_locale_directory(self.locale)

            # Merge: Target overrides Fallback
            self.translations = self._deep_merge(self.fallback_translations, target_data)
        else:
            self.translations = self.fallback_translations

    def _load_locale_directory(self, locale_code: str) -> Dict[str, Any]:
        """
        Scans a directory (e.g. 'it') and loads ALL .json files found inside.

        Args:
            locale_code: The folder name to look for (from settings).
        """
        merged_data = {}
        # Dynamic path construction: resources/i18n/it
        target_dir = self.i18n_root / locale_code

        if not target_dir.exists():
            return {}

        # Load all .json files in that folder alphabetically
        for file_path in sorted(target_dir.glob('*.json')):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    file_data = json.load(f)
                    merged_data = self._deep_merge(merged_data, file_data)
            except (OSError, json.JSONDecodeError) as e:
                print(f"Error loading i18n file {file_path.name}: {e}")

        return merged_data

    def _deep_merge(self, base: Dict, update: Dict) -> Dict:
        """Recursive merge of dictionaries."""
        result = base.copy()
        for key, value in update.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = value
        return result

    def t(self, key: str, **kwargs) -> str:
        """Retrieves a translated string."""
        keys = key.split('.')
        value = self.translations

        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
            else:
                value = None
                break

        if value is None:
            return f"[{key}]"

        if not isinstance(value, str):
            return f"[{key}]"

        if kwargs:
            try:
                return value.format(**kwargs)
            except (ValueError, KeyError, IndexError):
                return value

        return value


_i18n_instance: Optional[I18n] = None


def init_i18n(locale: str = 'en') -> I18n:
    global _i18n_instance
    _i18n_instance = I18n(locale)
    return _i18n_instance


def t(key: str, **kwargs) -> str:
    if _i18n_instance is None:
        init_i18n()
    return _i18n_instance.t(key, **kwargs)