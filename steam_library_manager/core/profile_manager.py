#
# steam_library_manager/core/profile_manager.py
# Steam user profiles: detection, switching, persistence
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

from steam_library_manager.config import config
from steam_library_manager.services.filter_service import ALL_PLATFORM_KEYS, ALL_TYPE_KEYS

logger = logging.getLogger("steamlibmgr.profile_manager")

__all__ = ["Profile", "ProfileManager"]


@dataclass(frozen=True)
class Profile:
    """Immutable categorization profile snapshot.

    Stores collections, autocat settings, filters, sort key.
    Persisted as individual JSON files.
    """

    name: str
    collections: tuple = ()
    autocat_methods: tuple = ()
    tags_per_game: int = 13
    ignore_common_tags: bool = True
    filter_enabled_types: frozenset = ALL_TYPE_KEYS
    filter_enabled_platforms: frozenset = ALL_PLATFORM_KEYS
    filter_active_statuses: frozenset = frozenset()
    filter_active_languages: frozenset = frozenset()
    sort_key: str = "name"
    created_at: float = 0.0


def _serialize_profile(prof):
    # profile -> JSON dict
    return {
        "name": prof.name,
        "created_at": prof.created_at,
        "collections": list(prof.collections),
        "autocat": {
            "methods": list(prof.autocat_methods),
            "tags_per_game": prof.tags_per_game,
            "ignore_common_tags": prof.ignore_common_tags,
        },
        "filters": {
            "enabled_types": sorted(prof.filter_enabled_types),
            "enabled_platforms": sorted(prof.filter_enabled_platforms),
            "active_statuses": sorted(prof.filter_active_statuses),
            "active_languages": sorted(prof.filter_active_languages),
        },
        "sort_key": prof.sort_key,
    }


def _deserialize_profile(data):
    # JSON dict -> Profile
    if "name" not in data:
        raise KeyError("Profile JSON missing 'name'")

    ac = data.get("autocat", {})
    flt = data.get("filters", {})

    return Profile(
        name=data["name"],
        created_at=data.get("created_at", 0.0),
        collections=tuple(data.get("collections", ())),
        autocat_methods=tuple(ac.get("methods", ())),
        tags_per_game=ac.get("tags_per_game", 13),
        ignore_common_tags=ac.get("ignore_common_tags", True),
        filter_enabled_types=frozenset(flt.get("enabled_types", ALL_TYPE_KEYS)),
        filter_enabled_platforms=frozenset(flt.get("enabled_platforms", ALL_PLATFORM_KEYS)),
        filter_active_statuses=frozenset(flt.get("active_statuses", ())),
        filter_active_languages=frozenset(flt.get("active_languages", ())),
        sort_key=data.get("sort_key", data.get("view_mode", "name")),
    )


def _sanitize_filename(name):
    # filesystem-safe profile name
    s = re.sub(r"[^\w\s\-]", "_", name, flags=re.UNICODE)
    return s.strip()


class ProfileManager:
    """CRUD for profile JSON files.

    Each profile is one JSON file in the profiles dir.
    """

    def __init__(self, profiles_dir=None):
        self.profiles_dir = profiles_dir or config.DATA_DIR / "profiles"
        self.profiles_dir.mkdir(parents=True, exist_ok=True)

    def save_profile(self, profile):
        if not profile.name or not profile.name.strip():
            raise ValueError("Profile name cannot be empty")

        fp = self.profiles_dir / ("%s.json" % _sanitize_filename(profile.name))

        data = _serialize_profile(profile)
        with open(fp, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        logger.info("saved profile '%s' to %s" % (profile.name, fp))
        return fp

    def load_profile(self, name):
        fp = self.profiles_dir / ("%s.json" % _sanitize_filename(name))

        if not fp.exists():
            raise FileNotFoundError("profile '%s' not found at %s" % (name, fp))

        with open(fp, "r", encoding="utf-8") as f:
            data = json.load(f)

        return _deserialize_profile(data)

    def delete_profile(self, name):
        fp = self.profiles_dir / ("%s.json" % _sanitize_filename(name))

        if not fp.exists():
            return False

        fp.unlink()
        logger.info("deleted profile '%s'" % name)
        return True

    def list_profiles(self):
        # returns [(name, created_at), ...] sorted newest first
        out = []

        for jf in sorted(self.profiles_dir.glob("*.json")):
            try:
                with open(jf, "r", encoding="utf-8") as f:
                    data = json.load(f)
                nm = data.get("name", jf.stem)
                ts = data.get("created_at", 0.0)
                out.append((nm, ts))
            except (json.JSONDecodeError, OSError) as exc:
                logger.warning("skipping corrupt profile %s: %s" % (jf.name, exc))

        out.sort(key=lambda x: x[1], reverse=True)
        return out

    def rename_profile(self, old_name, new_name):
        if not new_name or not new_name.strip():
            raise ValueError("New profile name cannot be empty")

        try:
            old = self.load_profile(old_name)
        except FileNotFoundError:
            return False

        renamed = replace(old, name=new_name.strip())

        self.save_profile(renamed)
        if _sanitize_filename(old_name) != _sanitize_filename(new_name):
            self.delete_profile(old_name)

        logger.info("renamed profile '%s' -> '%s'" % (old_name, new_name))
        return True

    def export_profile(self, name, target_path):
        src = self.profiles_dir / ("%s.json" % _sanitize_filename(name))

        if not src.exists():
            return False

        shutil.copy2(src, target_path)
        logger.info("exported profile '%s' to %s" % (name, target_path))
        return True

    def import_profile(self, source_path):
        if not source_path.exists():
            raise FileNotFoundError("import source not found: %s" % source_path)

        with open(source_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        prof = _deserialize_profile(data)

        if prof.created_at == 0.0:
            prof = replace(prof, created_at=time.time())

        self.save_profile(prof)
        logger.info("imported profile '%s' from %s" % (prof.name, source_path))
        return prof
