# src/core/profile_manager.py

"""Profile management for Steam Library Manager.

Provides a frozen Profile dataclass and ProfileManager for CRUD operations
on categorization profiles. Profiles store collections, filter states,
AutoCat settings, and view mode as JSON files in the profiles directory.
"""

from __future__ import annotations

import json
import logging
import re
import shutil
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from src.config import config
from src.services.filter_service import ALL_PLATFORM_KEYS, ALL_TYPE_KEYS

logger = logging.getLogger("steamlibmgr.profile_manager")

__all__ = ["Profile", "ProfileManager"]


@dataclass(frozen=True)
class Profile:
    """Immutable snapshot of a categorization profile.

    Attributes:
        name: Display name of the profile.
        collections: Tuple of collection dicts (deep-copied from cloud storage).
        autocat_methods: Enabled AutoCat method names.
        tags_per_game: Max tags per game for AutoCat.
        ignore_common_tags: Whether to ignore common tags in AutoCat.
        filter_enabled_types: Enabled type filter keys.
        filter_enabled_platforms: Enabled platform filter keys.
        filter_active_statuses: Active status filter keys.
        view_mode: Current view mode identifier.
        created_at: Unix timestamp of profile creation.
    """

    name: str
    collections: tuple[dict[str, Any], ...] = ()
    autocat_methods: tuple[str, ...] = ()
    tags_per_game: int = 13
    ignore_common_tags: bool = True
    filter_enabled_types: frozenset[str] = ALL_TYPE_KEYS
    filter_enabled_platforms: frozenset[str] = ALL_PLATFORM_KEYS
    filter_active_statuses: frozenset[str] = frozenset()
    view_mode: str = "details"
    created_at: float = 0.0


def _serialize_profile(profile: Profile) -> dict[str, Any]:
    """Converts a Profile to a JSON-serializable dict.

    Args:
        profile: The profile to serialize.

    Returns:
        Dictionary ready for JSON serialization.
    """
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
        },
        "view_mode": profile.view_mode,
    }


def _deserialize_profile(data: dict[str, Any]) -> Profile:
    """Constructs a Profile from a deserialized JSON dict.

    Missing optional fields fall back to Profile defaults.

    Args:
        data: Dictionary loaded from a profile JSON file.

    Returns:
        A frozen Profile instance.

    Raises:
        KeyError: If the required ``name`` field is missing.
    """
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
        view_mode=data.get("view_mode", "details"),
    )


def _sanitize_filename(name: str) -> str:
    """Converts a profile name into a safe filesystem name.

    Replaces non-alphanumeric characters (except spaces, hyphens, underscores)
    with underscores and strips leading/trailing whitespace.

    Args:
        name: The raw profile name.

    Returns:
        A filesystem-safe string (without extension).
    """
    safe = re.sub(r"[^\w\s\-]", "_", name, flags=re.UNICODE)
    return safe.strip()


class ProfileManager:
    """Manages profile CRUD operations on the filesystem.

    Profiles are stored as individual JSON files in a configurable directory.
    Each file is named after a sanitized version of the profile name.

    Attributes:
        profiles_dir: Path to the directory where profile JSON files are stored.
    """

    def __init__(self, profiles_dir: Path | None = None) -> None:
        """Initializes the ProfileManager.

        Args:
            profiles_dir: Override for the profiles directory.
                Defaults to ``config.DATA_DIR / "profiles"``.
        """
        self.profiles_dir: Path = profiles_dir or config.DATA_DIR / "profiles"
        self.profiles_dir.mkdir(parents=True, exist_ok=True)

    def save_profile(self, profile: Profile) -> Path:
        """Serializes and saves a profile to a JSON file.

        If a profile with the same name already exists, it is overwritten.

        Args:
            profile: The profile to save.

        Returns:
            Path to the written JSON file.

        Raises:
            ValueError: If the profile name is empty.
        """
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
        """Loads a profile from its JSON file.

        Args:
            name: The profile name (used to derive the filename).

        Returns:
            The deserialized Profile.

        Raises:
            FileNotFoundError: If the profile file does not exist.
        """
        safe_name = _sanitize_filename(name)
        file_path = self.profiles_dir / f"{safe_name}.json"

        if not file_path.exists():
            raise FileNotFoundError(f"Profile '{name}' not found at {file_path}")

        with open(file_path, "r", encoding="utf-8") as fh:
            data = json.load(fh)

        return _deserialize_profile(data)

    def delete_profile(self, name: str) -> bool:
        """Deletes a profile JSON file.

        Args:
            name: The profile name to delete.

        Returns:
            True if the file was deleted, False if it did not exist.
        """
        safe_name = _sanitize_filename(name)
        file_path = self.profiles_dir / f"{safe_name}.json"

        if not file_path.exists():
            return False

        file_path.unlink()
        logger.info("Deleted profile '%s'", name)
        return True

    def list_profiles(self) -> list[tuple[str, float]]:
        """Lists all saved profiles.

        Scans the profiles directory for JSON files and reads their metadata.

        Returns:
            List of ``(name, created_at)`` tuples, sorted by creation time
            (newest first).
        """
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
        """Renames an existing profile.

        Loads the old profile, creates a new one with the updated name
        (preserving the original creation timestamp), saves it, and
        deletes the old file.

        Args:
            old_name: Current profile name.
            new_name: Desired new profile name.

        Returns:
            True if the rename succeeded, False if the old profile was not found.

        Raises:
            ValueError: If the new name is empty.
        """
        if not new_name or not new_name.strip():
            raise ValueError("New profile name cannot be empty")

        try:
            old_profile = self.load_profile(old_name)
        except FileNotFoundError:
            return False

        # Build renamed profile, preserving original created_at
        renamed = Profile(
            name=new_name.strip(),
            collections=old_profile.collections,
            autocat_methods=old_profile.autocat_methods,
            tags_per_game=old_profile.tags_per_game,
            ignore_common_tags=old_profile.ignore_common_tags,
            filter_enabled_types=old_profile.filter_enabled_types,
            filter_enabled_platforms=old_profile.filter_enabled_platforms,
            filter_active_statuses=old_profile.filter_active_statuses,
            view_mode=old_profile.view_mode,
            created_at=old_profile.created_at,
        )

        self.save_profile(renamed)
        # Only delete old if filename actually changed
        if _sanitize_filename(old_name) != _sanitize_filename(new_name):
            self.delete_profile(old_name)

        logger.info("Renamed profile '%s' -> '%s'", old_name, new_name)
        return True

    def export_profile(self, name: str, target_path: Path) -> bool:
        """Exports a profile JSON to an external location.

        Args:
            name: The profile name to export.
            target_path: Destination file path.

        Returns:
            True if the export succeeded, False if the source was not found.
        """
        safe_name = _sanitize_filename(name)
        source = self.profiles_dir / f"{safe_name}.json"

        if not source.exists():
            return False

        shutil.copy2(source, target_path)
        logger.info("Exported profile '%s' to %s", name, target_path)
        return True

    def import_profile(self, source_path: Path) -> Profile:
        """Imports a profile from an external JSON file.

        Validates the JSON structure, saves a local copy, and returns
        the imported Profile.

        Args:
            source_path: Path to the external profile JSON file.

        Returns:
            The imported Profile.

        Raises:
            FileNotFoundError: If the source file does not exist.
            json.JSONDecodeError: If the file contains invalid JSON.
            KeyError: If the required ``name`` field is missing.
        """
        if not source_path.exists():
            raise FileNotFoundError(f"Import source not found: {source_path}")

        with open(source_path, "r", encoding="utf-8") as fh:
            data = json.load(fh)

        profile = _deserialize_profile(data)

        # Stamp import time if no creation time was set
        if profile.created_at == 0.0:
            profile = Profile(
                name=profile.name,
                collections=profile.collections,
                autocat_methods=profile.autocat_methods,
                tags_per_game=profile.tags_per_game,
                ignore_common_tags=profile.ignore_common_tags,
                filter_enabled_types=profile.filter_enabled_types,
                filter_enabled_platforms=profile.filter_enabled_platforms,
                filter_active_statuses=profile.filter_active_statuses,
                view_mode=profile.view_mode,
                created_at=time.time(),
            )

        self.save_profile(profile)
        logger.info("Imported profile '%s' from %s", profile.name, source_path)
        return profile
