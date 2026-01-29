# src/utils/i18n.py

"""
Internationalization (i18n) system for the Steam Library Manager.

This module provides a simple translation system that loads locale files
(JSON) and provides a translation function `t()` for retrieving localized
strings with placeholder support.
"""
import json
from pathlib import Path
from typing import Optional, Dict, Any


class I18n:
    """
    Core internationalization class.

    This class loads translation files from the locales directory and provides
    methods to retrieve translated strings with placeholder substitution.
    """

    def __init__(self, locale: str = 'en'):
        """
        Initializes the I18n system.

        Args:
            locale (str): The locale code (e.g., 'en', 'de'). Defaults to 'en'.
        """
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
        """
        Loads translation files from the locales directory.

        This method always loads English as a fallback, then loads the target
        locale if it's different from English.
        """
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
        """
        Retrieves a translated string for the given key.

        This method supports nested keys using dot notation (e.g., 'ui.menu.file')
        and placeholder substitution using Python's str.format() syntax.

        Args:
            key (str): The translation key in dot notation (e.g., 'ui.menu.file').
            **kwargs: Placeholder values for string formatting.

        Returns:
            str: The translated string with placeholders replaced, or a fallback
                string if the key is not found (e.g., '[ui.menu.file]').
        """
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
    """
    Initializes the global i18n instance.

    This function creates a new I18n instance and sets it as the global instance
    used by the `t()` function.

    Args:
        locale (str): The locale code (e.g., 'en', 'de'). Defaults to 'en'.

    Returns:
        I18n: The initialized I18n instance.
    """
    global _i18n_instance
    _i18n_instance = I18n(locale)
    return _i18n_instance


def t(key: str, **kwargs) -> str:
    """
    Global translation function.

    This is a convenience function that uses the global I18n instance to retrieve
    translated strings. If no instance exists, it initializes one with the default
    locale ('en').

    Args:
        key (str): The translation key in dot notation (e.g., 'ui.menu.file').
        **kwargs: Placeholder values for string formatting.

    Returns:
        str: The translated string with placeholders replaced.
    """
    if _i18n_instance is None:
        init_i18n()
    return _i18n_instance.t(key, **kwargs)
