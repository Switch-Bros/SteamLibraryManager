#
# steam_library_manager/services/autocat_preset_manager.py
# Saving and loading auto-categorization presets as JSON
#
# Copyright (c) 2025-2026 SwitchBros
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
    """Immutable auto-categorization preset."""

    name: str
    methods: tuple[str, ...] = field(default_factory=tuple)
    tags_count: int = 13
    ignore_common: bool = True
    curator_url: str | None = None
    curator_recommendations: tuple[str, ...] | None = None


class AutoCatPresetManager:
    """CRUD operations for auto-categorization presets stored as JSON."""

    def __init__(self, data_dir: Path | None = None) -> None:
        self._data_dir = data_dir or config.DATA_DIR
        self._file_path = self._data_dir / "autocat_presets.json"

    def load_presets(self) -> list[AutoCatPreset]:
        """Load all presets from disk."""
        data = load_json(self._file_path, default=[])
        if not data:
            return []

        presets: list[AutoCatPreset] = []
        for item in data:
            try:
                presets.append(
                    AutoCatPreset(
                        name=item["name"],
                        methods=tuple(item.get("methods", ())),
                        tags_count=item.get("tags_count", 13),
                        ignore_common=item.get("ignore_common", True),
                        curator_url=item.get("curator_url"),
                        curator_recommendations=(
                            tuple(item["curator_recommendations"]) if item.get("curator_recommendations") else None
                        ),
                    )
                )
            except (KeyError, TypeError) as exc:
                logger.warning("Skipping malformed preset: %s", exc)
                continue

        return presets

    def save_preset(self, preset: AutoCatPreset) -> None:
        """Save or update a preset. Overwrites existing with same name."""
        presets = self.load_presets()

        # Replace existing preset with same name
        presets = [p for p in presets if p.name != preset.name]
        presets.append(preset)

        self._write_presets(presets)
        logger.info("Saved preset '%s'", preset.name)

    def delete_preset(self, name: str) -> bool:
        """Delete a preset by name. Returns True if found and deleted."""
        presets = self.load_presets()
        original_count = len(presets)
        presets = [p for p in presets if p.name != name]

        if len(presets) == original_count:
            return False

        self._write_presets(presets)
        logger.info("Deleted preset '%s'", name)
        return True

    def rename_preset(self, old_name: str, new_name: str) -> bool:
        """Rename a preset. Returns True if old_name was found."""
        presets = self.load_presets()
        found = False

        new_presets: list[AutoCatPreset] = []
        for p in presets:
            if p.name == old_name:
                # Create new frozen instance with updated name
                new_presets.append(
                    AutoCatPreset(
                        name=new_name,
                        methods=p.methods,
                        tags_count=p.tags_count,
                        ignore_common=p.ignore_common,
                        curator_url=p.curator_url,
                        curator_recommendations=p.curator_recommendations,
                    )
                )
                found = True
            else:
                new_presets.append(p)

        if found:
            self._write_presets(new_presets)
            logger.info("Renamed preset '%s' -> '%s'", old_name, new_name)

        return found

    def _write_presets(self, presets: list[AutoCatPreset]) -> None:
        data = []
        for p in presets:
            d = asdict(p)
            # Convert tuples to lists for JSON serialization
            d["methods"] = list(d["methods"])
            if d["curator_recommendations"] is not None:
                d["curator_recommendations"] = list(d["curator_recommendations"])
            data.append(d)

        save_json(self._file_path, data)
