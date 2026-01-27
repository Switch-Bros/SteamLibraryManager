"""
i18n System - Core Translation Logic (Robust Path Fix)
"""
import json
from pathlib import Path
from typing import Optional, Dict, Any


class I18n:
    def __init__(self, locale: str = 'en'):
        self.locale = locale
        self.translations: Dict[str, Any] = {}
        self.fallback_translations: Dict[str, Any] = {}

        # Navigate safely to project root folder
        # File is in: PROJECT/src/utils/i18n.py
        # We want:    PROJECT/locales
        current_file = Path(__file__).resolve()
        project_root = current_file.parent.parent.parent
        self.locales_dir = project_root / 'locales'

        self._load_translations()

    def _load_translations(self):
        # Always load English as fallback
        fallback_path = self.locales_dir / 'en.json'
        if fallback_path.exists():
            try:
                with open(fallback_path, 'r', encoding='utf-8') as f:
                    self.fallback_translations = json.load(f)
            except (OSError, json.JSONDecodeError) as e:
                print(f"CRITICAL: Error loading fallback locale: {e}")
        else:
            # Fallback if we're in wrong directory (debugging)
            print(f"DEBUG: Locales not found at {fallback_path}")

        # Load target locale
        if self.locale != 'en':
            locale_path = self.locales_dir / f'{self.locale}.json'
            if locale_path.exists():
                try:
                    with open(locale_path, 'r', encoding='utf-8') as f:
                        self.translations = json.load(f)
                except (OSError, json.JSONDecodeError):
                    self.translations = self.fallback_translations.copy()
            else:
                self.translations = self.fallback_translations.copy()
        else:
            self.translations = self.fallback_translations.copy()

    def t(self, key: str, **kwargs) -> str:
        keys = key.split('.')

        # Try target locale
        value = self.translations
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
            else:
                value = None
                break

        # Try fallback
        if value is None:
            value = self.fallback_translations
            for k in keys:
                if isinstance(value, dict):
                    value = value.get(k)
                else:
                    value = None
                    break

        if value is None:
            return f"[{key}]"

        if not isinstance(value, str):
            return f"[{key}: not a string]"

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