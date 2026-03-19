#
# steam_library_manager/utils/i18n.py
# Internationalization system providing the t() translation function
#
# Copyright © 2025-2026 SwitchBros
# Licensed under the MIT License. See LICENSE for details.
#

from __future__ import annotations

import json
import logging
from pathlib import Path

__all__ = ["I18n", "get_language", "init_i18n", "t"]

logger = logging.getLogger("steamlibmgr.i18n")


class I18n:
    """Core i18n class. Loads shared files then locale-specific."""

    def __init__(self, locale="en"):
        self.locale = locale
        self._tr = {}  # translations
        self._fb = {}  # fallback

        from steam_library_manager.utils.paths import get_resources_dir

        self._root = get_resources_dir() / "i18n"
        self._load()

    def _load(self):
        # priority: shared -> english fallback -> target locale
        shared = self._load_shared()
        en = self._load_locale("en")
        self._fb = self._merge(shared, en)

        if self.locale == "en":
            self._tr = self._fb
        else:
            target = self._load_locale(self.locale)
            self._tr = self._merge(self._fb, target)

    def _load_dir(self, d: Path):
        # load and deep-merge all *.json from directory
        res = {}
        if not d.exists():
            return res

        for fp in sorted(d.glob("*.json")):
            try:
                with open(fp, "r", encoding="utf-8") as fh:
                    res = self._merge(res, json.load(fh))
            except (OSError, json.JSONDecodeError) as exc:
                logger.error("Error loading i18n file %s: %s" % (fp.name, exc))
        return res

    def _load_shared(self):
        # language-agnostic files in i18n root
        return self._load_dir(self._root)

    def _load_locale(self, code):
        return self._load_dir(self._root / code)

    def _merge(self, base, upd):
        # recursive dict merge, upd wins
        res = base.copy()
        for k, v in upd.items():
            if k in res and isinstance(res[k], dict) and isinstance(v, dict):
                res[k] = self._merge(res[k], v)
            else:
                res[k] = v
        return res

    def t(self, key, **kw):
        # lookup dot-notation key, return '[key]' if missing
        pts = key.split(".")
        cur = self._tr

        for p in pts:
            if isinstance(cur, dict):
                cur = cur.get(p)
            else:
                cur = None
                break

        if cur is None or not isinstance(cur, str):
            return "[%s]" % key

        if kw:
            try:
                return cur.format(**kw)
            except (ValueError, KeyError, IndexError):
                return cur

        return cur


_i18n = None  # singleton instance


def init_i18n(locale="en"):
    # setup global i18n singleton
    global _i18n
    _i18n = I18n(locale)
    return _i18n


def get_language():
    # return active locale code (e.g. 'en', 'de')
    if _i18n is None:
        init_i18n()
    return _i18n.locale


def t(key, **kw):
    # translate key via global instance
    if _i18n is None:
        init_i18n()
    return _i18n.t(key, **kw)
