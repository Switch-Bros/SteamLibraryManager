#
# steam_library_manager/utils/smart_collection_exporter.py
# Exports smart collections to a portable JSON sidecar format
#
# Copyright (c) 2025-2026 SwitchBros
# Licensed under the MIT License. See LICENSE for details.
#

from __future__ import annotations

import json
import logging
from pathlib import Path

from steam_library_manager.services.smart_collections.models import (
    SmartCollection,
    group_to_dict,
    rule_to_dict,
)

__all__ = ["SmartCollectionExporter"]

logger = logging.getLogger("steamlibmgr.smart_collection_exporter")

_FORMAT_VERSION = "1.1"


class SmartCollectionExporter:
    """Exports Smart Collections to portable JSON."""

    @staticmethod
    def export(collections: list[SmartCollection], output_path: Path) -> None:
        # write collections to JSON file
        # creates parent dirs if needed
        output_path.parent.mkdir(parents=True, exist_ok=True)

        payload = {
            "version": _FORMAT_VERSION,
            "count": len(collections),
            "smart_collections": [SmartCollectionExporter._collection_to_dict(sc) for sc in collections],
        }

        with open(output_path, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, indent=2, ensure_ascii=False)

        logger.info("Exported %d smart collections to %s" % (len(collections), output_path))

    @staticmethod
    def _collection_to_dict(collection: SmartCollection) -> dict:
        # serialize collection to dict
        # uses groups format (v1.1) if available, else flat rules (v1.0)
        result = {
            "name": collection.name,
            "description": collection.description,
            "icon": collection.icon,
            "logic": collection.logic.value,
            "auto_sync": collection.auto_sync,
        }

        if collection.groups:
            result["groups"] = [group_to_dict(g) for g in collection.groups]
        else:
            result["rules"] = [rule_to_dict(r) for r in collection.rules]

        return result
