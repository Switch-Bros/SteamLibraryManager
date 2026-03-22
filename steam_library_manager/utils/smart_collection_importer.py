#
# steam_library_manager/utils/smart_collection_importer.py
# Imports smart collections from JSON sidecar files
# FIXME: no schema validation on import
#
# Copyright © 2025-2026 SwitchBros
# Licensed under the MIT License. See LICENSE for details.
#

from __future__ import annotations

import json
import logging
from pathlib import Path

from steam_library_manager.services.smart_collections.models import (
    LogicOperator,
    SmartCollection,
    group_from_dict,
    rule_from_dict,
)

__all__ = ["SmartCollectionImporter"]

logger = logging.getLogger("steamlibmgr.smart_collection_importer")


class SmartCollectionImporter:
    """Imports Smart Collections from JSON format."""

    @staticmethod
    def import_collections(file_path: Path) -> list[SmartCollection]:
        # import from JSON file, supports v1.0 and v1.1 format
        if not file_path.exists():
            msg = "File not found: %s" % file_path
            raise FileNotFoundError(msg)

        with open(file_path, encoding="utf-8") as fh:
            try:
                data = json.load(fh)
            except json.JSONDecodeError as exc:
                msg = "Invalid JSON: %s" % exc
                raise ValueError(msg) from exc

        if not isinstance(data, dict) or "smart_collections" not in data:
            msg = "Missing 'smart_collections' key in JSON"
            raise ValueError(msg)

        raw = data["smart_collections"]
        if not isinstance(raw, list):
            msg = "'smart_collections' must be a list"
            raise ValueError(msg)

        out = []
        for entry in raw:
            try:
                sc = SmartCollectionImporter._dict_to_collection(entry)
                out.append(sc)
            except (ValueError, KeyError) as exc:
                logger.warning("Skipping invalid collection entry: %s" % exc)

        logger.info("Imported %d smart collections from %s" % (len(out), file_path))
        return out

    @staticmethod
    def _dict_to_collection(data: dict) -> SmartCollection:
        # dict -> SmartCollection
        name = data.get("name", "").strip()
        if not name:
            msg = "Collection name is required"
            raise ValueError(msg)

        # Parse logic operator
        lstr = data.get("logic", "OR")
        try:
            logic = LogicOperator(lstr)
        except ValueError:
            logger.warning("Unknown logic '%s', defaulting to OR" % lstr)
            logic = LogicOperator.OR

        groups = []
        rules = []

        # v1.1 format: groups
        if "groups" in data:
            rgroups = data["groups"]
            if not isinstance(rgroups, list):
                msg = "'groups' must be a list"
                raise ValueError(msg)
            for gd in rgroups:
                groups.append(group_from_dict(gd))
        else:
            # v1.0 format: flat rules
            rrules = data.get("rules", [])
            if not isinstance(rrules, list):
                msg = "'rules' must be a list"
                raise ValueError(msg)
            for rd in rrules:
                rules.append(rule_from_dict(rd))

        return SmartCollection(
            name=name,
            description=data.get("description", ""),
            icon=data.get("icon", "\U0001f9e0"),
            logic=logic,
            rules=rules,
            groups=groups,
            auto_sync=data.get("auto_sync", True),
        )
