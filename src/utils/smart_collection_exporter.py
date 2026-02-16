# src/utils/smart_collection_exporter.py

"""Exports Smart Collections to a portable JSON file.

Serializes all Smart Collection rules, logic operators, and metadata
into a self-contained JSON format for backup, sharing, or migration.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from src.services.smart_collections.models import (
    SmartCollection,
    rule_to_dict,
)

__all__ = ["SmartCollectionExporter"]

logger = logging.getLogger("steamlibmgr.smart_collection_exporter")

_FORMAT_VERSION = "1.0"


class SmartCollectionExporter:
    """Exports Smart Collections to JSON format.

    The exported JSON contains all collection metadata and rules,
    but NOT the list of matched games (those are re-evaluated on import).
    """

    @staticmethod
    def export(collections: list[SmartCollection], output_path: Path) -> None:
        """Exports a list of Smart Collections to a JSON file.

        Args:
            collections: The Smart Collections to export.
            output_path: The file path to write the JSON to.

        Raises:
            OSError: If the file cannot be written.
        """
        output_path.parent.mkdir(parents=True, exist_ok=True)

        payload = {
            "version": _FORMAT_VERSION,
            "count": len(collections),
            "smart_collections": [SmartCollectionExporter._collection_to_dict(sc) for sc in collections],
        }

        with open(output_path, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, indent=2, ensure_ascii=False)

        logger.info("Exported %d smart collections to %s", len(collections), output_path)

    @staticmethod
    def _collection_to_dict(collection: SmartCollection) -> dict:
        """Serializes a SmartCollection to a portable dict.

        Args:
            collection: The Smart Collection to serialize.

        Returns:
            Dict with name, description, icon, logic, auto_sync, and rules.
        """
        return {
            "name": collection.name,
            "description": collection.description,
            "icon": collection.icon,
            "logic": collection.logic.value,
            "auto_sync": collection.auto_sync,
            "rules": [rule_to_dict(r) for r in collection.rules],
        }
