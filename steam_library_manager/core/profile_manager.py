#
# steam_library_manager/core/profile_manager.py
# Profile CRUD - collections, filters, AutoCat settings as JSON files
#
# Copyright © 2025-2026 SwitchBros
# Licensed under the MIT License. See LICENSE for details.
#

from __future__ import annotations

import json
import logging
import re
import shutil
import time
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any

from steam_library_manager.config import config
from steam_library_manager.services.filter_service import ALL_PLATFORM_KEYS, ALL_TYPE_KEYS

logger = logging.getLogger("steamlibmgr.profile_manager")

__all__ = ["Profile", "ProfileManager"]


@dataclass(frozen=True)
class Profile:
    """Immutable snapshot of a categorization profile."""

    name: str
    collections: tuple[dict[str, Any], ...] = ()
    autocat_methods: tuple[str, ...] = ()
    tags_per_game: int = 13
    ignore_common_tags: bool = True
    filter_enabled_types: frozenset[str] = ALL_TYPE_KEYS
    filter_enabled_platforms: frozenset[str] = ALL_PLATFORM_KEYS
    filter_active_statuses: frozenset[str] = frozenset()
    filter_active_languages: frozenset[str] = frozenset()
    sort_key: str = "name"
    created_at: float = 0.0


def _serialize_profile(profile: Profile) -> dict[str, Any]:
    return {
        "name": profile.name,
        "created_at": profile.created_at,
        "collections": list(profile.collections),
        "autocat": {
            "methods": list(profile.autocat_methods),
            "tags_per_game": profile.tags_per_game,
            "ignore_common_tags": profile.ignore_common_tags,
        },
        "filters": {
            "enabled_types": sorted(profile.filter_enabled_types),
            "enabled_platforms": sorted(profile.filter_enabled_platforms),
            "active_statuses": sorted(profile.filter_active_statuses),
            "active_languages": sorted(profile.filter_active_languages),
        },
        "sort_key": profile.sort_key,
    }


def _deserialize_profile(data: dict[str, Any]) -> Profile:
    """Build a Profile from a JSON dict. Missing fields use defaults."""
    if "name" not in data:
        raise KeyError("Profile JSON is missing required 'name' field")

    autocat = data.get("autocat", {})
    filters = data.get("filters", {})

    return Profile(
        name=data["name"],
        created_at=data.get("created_at", 0.0),
        collections=tuple(data.get("collections", ())),
        autocat_methods=tuple(autocat.get("methods", ())),
        tags_per_game=autocat.get("tags_per_game", 13),
        ignore_common_tags=autocat.get("ignore_common_tags", True),
        filter_enabled_types=frozenset(filters.get("enabled_types", ALL_TYPE_KEYS)),
        filter_enabled_platforms=frozenset(filters.get("enabled_platforms", ALL_PLATFORM_KEYS)),
        filter_active_statuses=frozenset(filters.get("active_statuses", ())),
        filter_active_languages=frozenset(filters.get("active_languages", ())),
        sort_key=data.get("sort_key", data.get("view_mode", "name")),
    )


def _sanitize_filename(name: str) -> str:
    """Turn a profile name into a safe filename (no extension)."""
    safe = re.sub(r"[^\w\s\-]", "_", name, flags=re.UNICODE)
    return safe.strip()


class ProfileManager:
    """Profile CRUD on the filesystem. Each profile is a JSON file."""

    def __init__(self, profiles_dir: Path | None = None) -> None:
        self.profiles_dir: Path = profiles_dir or config.DATA_DIR / "profiles"
        self.profiles_dir.mkdir(parents=True, exist_ok=True)

    def save_profile(self, profile: Profile) -> Path:
        """Save profile to JSON, overwriting if it exists. Returns the file path."""
        if not profile.name or not profile.name.strip():
            raise ValueError("Profile name cannot be empty")

        safe_name = _sanitize_filename(profile.name)
        file_path = self.profiles_dir / f"{safe_name}.json"

        data = _serialize_profile(profile)
        with open(file_path, "w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=2, ensure_ascii=False)

        logger.info("Saved profile '%s' to %s", profile.name, file_path)
        return file_path

    def load_profile(self, name: str) -> Profile:
        safe_name = _sanitize_filename(name)
        file_path = self.profiles_dir / f"{safe_name}.json"

        if not file_path.exists():
            raise FileNotFoundError(f"Profile '{name}' not found at {file_path}")

        with open(file_path, "r", encoding="utf-8") as fh:
            data = json.load(fh)

        return _deserialize_profile(data)

    def delete_profile(self, name: str) -> bool:
        safe_name = _sanitize_filename(name)
        file_path = self.profiles_dir / f"{safe_name}.json"

        if not file_path.exists():
            return False

        file_path.unlink()
        logger.info("Deleted profile '%s'", name)
        return True

    def list_profiles(self) -> list[tuple[str, float]]:
        """Return (name, created_at) tuples for all profiles, newest first."""
        profiles: list[tuple[str, float]] = []

        for json_file in sorted(self.profiles_dir.glob("*.json")):
            try:
                with open(json_file, "r", encoding="utf-8") as fh:
                    data = json.load(fh)
                name = data.get("name", json_file.stem)
                created_at = data.get("created_at", 0.0)
                profiles.append((name, created_at))
            except (json.JSONDecodeError, OSError) as exc:
                logger.warning("Skipping corrupt profile %s: %s", json_file.name, exc)

        profiles.sort(key=lambda item: item[1], reverse=True)
        return profiles

    def rename_profile(self, old_name: str, new_name: str) -> bool:
        """Rename a profile, preserving its creation timestamp."""
        if not new_name or not new_name.strip():
            raise ValueError("New profile name cannot be empty")

        try:
            old_profile = self.load_profile(old_name)
        except FileNotFoundError:
            return False

        renamed = replace(old_profile, name=new_name.strip())

        self.save_profile(renamed)
        # Only delete old if filename actually changed
        if _sanitize_filename(old_name) != _sanitize_filename(new_name):
            self.delete_profile(old_name)

        logger.info("Renamed profile '%s' -> '%s'", old_name, new_name)
        return True

    def export_profile(self, name: str, target_path: Path) -> bool:
        safe_name = _sanitize_filename(name)
        source = self.profiles_dir / f"{safe_name}.json"

        if not source.exists():
            return False

        shutil.copy2(source, target_path)
        logger.info("Exported profile '%s' to %s", name, target_path)
        return True

    def import_profile(self, source_path: Path) -> Profile:
        """Import a profile from an external JSON file and save a local copy."""
        if not source_path.exists():
            raise FileNotFoundError(f"Import source not found: {source_path}")

        with open(source_path, "r", encoding="utf-8") as fh:
            data = json.load(fh)

        profile = _deserialize_profile(data)

        # Stamp import time if no creation time was set
        if profile.created_at == 0.0:
            profile = replace(profile, created_at=time.time())

        self.save_profile(profile)
        logger.info("Imported profile '%s' from %s", profile.name, source_path)
        return profile
