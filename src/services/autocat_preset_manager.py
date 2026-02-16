"""
AutoCat Preset Manager for saving and loading categorization presets.

Manages named presets of auto-categorization configurations,
persisted as JSON in the application data directory.
"""

from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass, field
from pathlib import Path

from src.config import config

logger = logging.getLogger("steamlibmgr.autocat_preset_manager")

__all__ = ["AutoCatPreset", "AutoCatPresetManager"]


@dataclass(frozen=True)
class AutoCatPreset:
    """Immutable representation of an auto-categorization preset.

    Args:
        name: Display name for the preset.
        methods: Tuple of method names to run (e.g. ("tags", "publisher")).
        tags_count: Number of tags per game (used when "tags" is in methods).
        ignore_common: Whether to ignore common tags.
        curator_url: Optional Steam Curator URL (used when "curator" is in methods).
        curator_recommendations: Optional tuple of recommendation types to include.
    """

    name: str
    methods: tuple[str, ...] = field(default_factory=tuple)
    tags_count: int = 13
    ignore_common: bool = True
    curator_url: str | None = None
    curator_recommendations: tuple[str, ...] | None = None


class AutoCatPresetManager:
    """Manages CRUD operations for auto-categorization presets.

    Presets are stored as a JSON array in the application data directory.
    """

    def __init__(self, data_dir: Path | None = None) -> None:
        """Initialize the preset manager.

        Args:
            data_dir: Directory for storing presets. Defaults to config.DATA_DIR.
        """
        self._data_dir = data_dir or config.DATA_DIR
        self._file_path = self._data_dir / "autocat_presets.json"

    def load_presets(self) -> list[AutoCatPreset]:
        """Load all presets from disk.

        Returns:
            List of presets, empty if file does not exist or is invalid.
        """
        if not self._file_path.exists():
            return []

        try:
            with open(self._file_path, encoding="utf-8") as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError) as exc:
            logger.warning("Failed to load presets from %s: %s", self._file_path, exc)
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
        """Save or update a preset.

        If a preset with the same name exists, it is overwritten.

        Args:
            preset: The preset to save.
        """
        presets = self.load_presets()

        # Replace existing preset with same name
        presets = [p for p in presets if p.name != preset.name]
        presets.append(preset)

        self._write_presets(presets)
        logger.info("Saved preset '%s'", preset.name)

    def delete_preset(self, name: str) -> bool:
        """Delete a preset by name.

        Args:
            name: Name of the preset to delete.

        Returns:
            True if a preset was deleted, False if not found.
        """
        presets = self.load_presets()
        original_count = len(presets)
        presets = [p for p in presets if p.name != name]

        if len(presets) == original_count:
            return False

        self._write_presets(presets)
        logger.info("Deleted preset '%s'", name)
        return True

    def rename_preset(self, old_name: str, new_name: str) -> bool:
        """Rename a preset.

        Args:
            old_name: Current name of the preset.
            new_name: New name for the preset.

        Returns:
            True if renamed, False if old_name not found.
        """
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
        """Write the full preset list to disk.

        Args:
            presets: List of presets to persist.
        """
        self._data_dir.mkdir(parents=True, exist_ok=True)

        data = []
        for p in presets:
            d = asdict(p)
            # Convert tuples to lists for JSON serialization
            d["methods"] = list(d["methods"])
            if d["curator_recommendations"] is not None:
                d["curator_recommendations"] = list(d["curator_recommendations"])
            data.append(d)

        with open(self._file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
