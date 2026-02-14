"""
Internationalization (i18n) system.

Loads translation files dynamically:
1. Shared files from resources/i18n/*.json (language-agnostic: emoji, logs)
2. Locale-specific files from resources/i18n/{locale}/*.json
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

__all__ = ["I18n", "init_i18n", "t"]

logger = logging.getLogger("steamlibmgr.i18n")


class I18n:
    """Core internationalization class.

    Loads shared files from resources/i18n/ root (emoji.json, logs.json),
    then locale-specific files from resources/i18n/{locale}/.
    """

    def __init__(self, locale: str = "en") -> None:
        """Initialize I18n with a specific locale code.

        Args:
            locale: The locale code used to find the corresponding
                directory in resources/i18n/.
        """
        self.locale = locale
        self.translations: dict[str, Any] = {}
        self.fallback_translations: dict[str, Any] = {}

        current_file = Path(__file__).resolve()
        project_root = current_file.parent.parent.parent
        self.i18n_root = project_root / "resources" / "i18n"

        self._load_translations()

    def _load_translations(self) -> None:
        """Load translations in priority order.

        1. Load shared files from resources/i18n/*.json (emoji, logs)
        2. Load English fallback from resources/i18n/en/*.json
        3. Deep-merge shared + English = fallback
        4. If locale != 'en': load target locale, merge on top of fallback
        """
        shared_data = self._load_shared_files()
        en_data = self._load_locale_directory("en")
        self.fallback_translations = self._deep_merge(shared_data, en_data)

        if self.locale != "en":
            target_data = self._load_locale_directory(self.locale)
            self.translations = self._deep_merge(self.fallback_translations, target_data)
        else:
            self.translations = self.fallback_translations

    def _load_shared_files(self) -> dict[str, Any]:
        """Load all JSON files from the i18n root directory.

        These are language-agnostic shared files (emoji.json, logs.json).

        Returns:
            Merged dictionary of all shared JSON files.
        """
        merged_data: dict[str, Any] = {}

        if not self.i18n_root.exists():
            return {}

        for file_path in sorted(self.i18n_root.glob("*.json")):
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    file_data = json.load(f)
                    merged_data = self._deep_merge(merged_data, file_data)
            except (OSError, json.JSONDecodeError) as e:
                logger.error("Error loading shared i18n file %s: %s", file_path.name, e)

        return merged_data

    def _load_locale_directory(self, locale_code: str) -> dict[str, Any]:
        """Load all JSON files from a locale directory.

        Args:
            locale_code: The folder name to look for (e.g. 'en', 'de').

        Returns:
            Merged dictionary of all JSON files in the locale directory.
        """
        merged_data: dict[str, Any] = {}
        target_dir = self.i18n_root / locale_code

        if not target_dir.exists():
            return {}

        for file_path in sorted(target_dir.glob("*.json")):
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    file_data = json.load(f)
                    merged_data = self._deep_merge(merged_data, file_data)
            except (OSError, json.JSONDecodeError) as e:
                logger.error("Error loading i18n file %s: %s", file_path.name, e)

        return merged_data

    def _deep_merge(self, base: dict[str, Any], update: dict[str, Any]) -> dict[str, Any]:
        """Recursive merge of dictionaries.

        Args:
            base: The base dictionary.
            update: The dictionary whose values override base.

        Returns:
            New dictionary with merged values.
        """
        result = base.copy()
        for key, value in update.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = value
        return result

    def t(self, key: str, **kwargs: Any) -> str:
        """Retrieve a translated string by dot-notation key.

        Args:
            key: Dot-separated key path (e.g. 'menu.file.root').
            **kwargs: Format arguments for string interpolation.

        Returns:
            Translated string, or '[key]' if not found.
        """
        keys = key.split(".")
        value: Any = self.translations

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


_i18n_instance: I18n | None = None


def init_i18n(locale: str = "en") -> I18n:
    """Initialize the global i18n instance.

    Args:
        locale: The locale code to use.

    Returns:
        The initialized I18n instance.
    """
    global _i18n_instance
    _i18n_instance = I18n(locale)
    return _i18n_instance


def t(key: str, **kwargs: Any) -> str:
    """Retrieve a translated string using the global i18n instance.

    Args:
        key: Dot-separated key path.
        **kwargs: Format arguments for string interpolation.

    Returns:
        Translated string, or '[key]' if not found.
    """
    if _i18n_instance is None:
        init_i18n()
    return _i18n_instance.t(key, **kwargs)
