#
# steam_library_manager/utils/smart_collection_importer.py
# Smart Collection import from portable JSON
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
    """Imports Smart Collections from JSON format (v1.0 and v1.1)."""

    @staticmethod
    def import_collections(file_path: Path) -> list[SmartCollection]:
        """Import Smart Collections from a JSON file."""
        if not file_path.exists():
            msg = f"File not found: {file_path}"
            raise FileNotFoundError(msg)

        with open(file_path, encoding="utf-8") as fh:
            try:
                data = json.load(fh)
            except json.JSONDecodeError as exc:
                msg = f"Invalid JSON: {exc}"
                raise ValueError(msg) from exc

        if not isinstance(data, dict) or "smart_collections" not in data:
            msg = "Missing 'smart_collections' key in JSON"
            raise ValueError(msg)

        raw_collections = data["smart_collections"]
        if not isinstance(raw_collections, list):
            msg = "'smart_collections' must be a list"
            raise ValueError(msg)

        result: list[SmartCollection] = []
        for entry in raw_collections:
            try:
                sc = SmartCollectionImporter._dict_to_collection(entry)
                result.append(sc)
            except (ValueError, KeyError) as exc:
                logger.warning("Skipping invalid collection entry: %s", exc)

        logger.info("Imported %d smart collections from %s", len(result), file_path)
        return result

    @staticmethod
    def _dict_to_collection(data: dict) -> SmartCollection:
        """Deserialize a single Smart Collection from a dict."""
        name = data.get("name", "").strip()
        if not name:
            msg = "Collection name is required"
            raise ValueError(msg)

        logic_str = data.get("logic", "OR")
        try:
            logic = LogicOperator(logic_str)
        except ValueError:
            logger.warning("Unknown logic '%s', defaulting to OR", logic_str)
            logic = LogicOperator.OR

        groups = []
        rules = []

        if "groups" in data:
            raw_groups = data["groups"]
            if not isinstance(raw_groups, list):
                msg = "'groups' must be a list"
                raise ValueError(msg)
            for group_data in raw_groups:
                groups.append(group_from_dict(group_data))
        else:
            raw_rules = data.get("rules", [])
            if not isinstance(raw_rules, list):
                msg = "'rules' must be a list"
                raise ValueError(msg)
            for rule_data in raw_rules:
                rules.append(rule_from_dict(rule_data))

        return SmartCollection(
            name=name,
            description=data.get("description", ""),
            icon=data.get("icon", "\U0001f9e0"),
            logic=logic,
            rules=rules,
            groups=groups,
            auto_sync=data.get("auto_sync", True),
        )
