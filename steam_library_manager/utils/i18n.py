#
# steam_library_manager/utils/i18n.py
# Internationalization system - loads translations from JSON files.
#
# Copyright © 2025-2026 SwitchBros
# Licensed under the MIT License. See LICENSE for details.
#

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

__all__ = ["I18n", "get_language", "init_i18n", "t"]

logger = logging.getLogger("steamlibmgr.i18n")


class I18n:
    """Core internationalization class.

    Loads shared files from resources/i18n/ root (emoji.json, logs.json),
    then locale-specific files from resources/i18n/{locale}/.
    """

    def __init__(self, locale: str = "en") -> None:
        self.locale = locale
        self.translations: dict[str, Any] = {}
        self.fallback_translations: dict[str, Any] = {}

        from steam_library_manager.utils.paths import get_resources_dir

        self.i18n_root = get_resources_dir() / "i18n"

        self._load_translations()

    def _load_translations(self) -> None:
        """Load shared files, English fallback, then target locale."""
        shared_data = self._load_shared_files()
        en_data = self._load_locale_directory("en")
        self.fallback_translations = self._deep_merge(shared_data, en_data)

        if self.locale != "en":
            target_data = self._load_locale_directory(self.locale)
            self.translations = self._deep_merge(self.fallback_translations, target_data)
        else:
            self.translations = self.fallback_translations

    def _load_json_directory(self, directory: Path) -> dict[str, Any]:
        """Load and deep-merge all JSON files from a directory."""
        merged: dict[str, Any] = {}
        if not directory.exists():
            return merged
        for file_path in sorted(directory.glob("*.json")):
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    merged = self._deep_merge(merged, json.load(f))
            except (OSError, json.JSONDecodeError) as e:
                logger.error("Error loading i18n file %s: %s", file_path.name, e)
        return merged

    def _load_shared_files(self) -> dict[str, Any]:
        return self._load_json_directory(self.i18n_root)

    def _load_locale_directory(self, locale_code: str) -> dict[str, Any]:
        return self._load_json_directory(self.i18n_root / locale_code)

    def _deep_merge(self, base: dict[str, Any], update: dict[str, Any]) -> dict[str, Any]:
        """Recursive dict merge - update values override base."""
        result = base.copy()
        for key, value in update.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = value
        return result

    def t(self, key: str, **kwargs: Any) -> str:
        """Look up a translated string by dot-notation key.

        Returns '[key]' if not found.
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
    """Initialize the global i18n instance."""
    global _i18n_instance
    _i18n_instance = I18n(locale)
    return _i18n_instance


def get_language() -> str:
    """Return the current locale code (e.g. 'en', 'de')."""
    if _i18n_instance is None:
        init_i18n()
    return _i18n_instance.locale


def t(key: str, **kwargs: Any) -> str:
    """Retrieve a translated string using the global i18n instance."""
    if _i18n_instance is None:
        init_i18n()
    return _i18n_instance.t(key, **kwargs)
