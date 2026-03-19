#
# steam_library_manager/services/autocat_preset_manager.py
# Manages user-defined and built-in auto-categorization presets
#
# Copyright © 2025-2026 SwitchBros
# Licensed under the MIT License. See LICENSE for details.
#

from __future__ import annotations

import logging
from dataclasses import asdict, dataclass, field
from pathlib import Path

from steam_library_manager.config import config
from steam_library_manager.utils.json_utils import load_json, save_json

logger = logging.getLogger("steamlibmgr.autocat_preset_manager")

__all__ = ["AutoCatPreset", "AutoCatPresetManager"]


@dataclass(frozen=True)
class AutoCatPreset:
    # immutable auto-categorization preset
    name: str
    methods: tuple[str, ...] = field(default_factory=tuple)
    tags_count: int = 13
    ignore_common: bool = True
    curator_url: str | None = None
    curator_recommendations: tuple[str, ...] | None = None


class AutoCatPresetManager:
    # CRUD for auto-categorization presets

    def __init__(self, data_dir: Path | None = None):
        self._dir = data_dir or config.DATA_DIR
        self._fp = self._dir / "autocat_presets.json"

    def load_presets(self):
        # load all presets from disk
        raw = load_json(self._fp, default=[])
        if not raw:
            return []

        res = []
        for it in raw:
            try:
                recs = it.get("curator_recommendations")
                res.append(
                    AutoCatPreset(
                        name=it["name"],
                        methods=tuple(it.get("methods", ())),
                        tags_count=it.get("tags_count", 13),
                        ignore_common=it.get("ignore_common", True),
                        curator_url=it.get("curator_url"),
                        curator_recommendations=tuple(recs) if recs else None,
                    )
                )
            except (KeyError, TypeError) as exc:
                logger.warning("Skipping malformed preset: %s" % exc)
                continue
        return res

    def save_preset(self, p):
        # overwrites existing preset with same name
        ps = [x for x in self.load_presets() if x.name != p.name]
        ps.append(p)
        self._write(ps)
        logger.info("Saved preset '%s'" % p.name)

    def delete_preset(self, n):
        # delete preset by name, return True if removed
        ps = self.load_presets()
        before = len(ps)
        ps = [x for x in ps if x.name != n]

        if len(ps) == before:
            return False

        self._write(ps)
        logger.info("Deleted preset '%s'" % n)
        return True

    def rename_preset(self, old, new):
        # rename preset, return False if not found
        ps = self.load_presets()
        ok = False

        res = []
        for p in ps:
            if p.name == old:
                res.append(
                    AutoCatPreset(
                        name=new,
                        methods=p.methods,
                        tags_count=p.tags_count,
                        ignore_common=p.ignore_common,
                        curator_url=p.curator_url,
                        curator_recommendations=p.curator_recommendations,
                    )
                )
                ok = True
            else:
                res.append(p)

        if ok:
            self._write(res)
            logger.info("Renamed preset '%s' -> '%s'" % (old, new))
        return ok

    def _write(self, ps):
        # serialize to JSON-safe dicts
        data = []
        for p in ps:
            d = asdict(p)
            d["methods"] = list(d["methods"])
            if d["curator_recommendations"] is not None:
                d["curator_recommendations"] = list(d["curator_recommendations"])
            data.append(d)
        save_json(self._fp, data)
