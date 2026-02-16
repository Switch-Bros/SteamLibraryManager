# src/utils/smart_collection_importer.py

"""Imports Smart Collections from a portable JSON file.

Deserializes Smart Collection rules and metadata from a JSON file
previously exported by SmartCollectionExporter.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from src.services.smart_collections.models import (
    LogicOperator,
    SmartCollection,
    rule_from_dict,
)

__all__ = ["SmartCollectionImporter"]

logger = logging.getLogger("steamlibmgr.smart_collection_importer")


class SmartCollectionImporter:
    """Imports Smart Collections from JSON format.

    Supports version 1.0 of the export format. Unknown fields are
    silently ignored for forward compatibility.
    """

    @staticmethod
    def import_collections(file_path: Path) -> list[SmartCollection]:
        """Imports Smart Collections from a JSON file.

        Args:
            file_path: Path to the JSON file to import.

        Returns:
            List of SmartCollection instances (without collection_id,
            ready to be created via SmartCollectionManager).

        Raises:
            FileNotFoundError: If the file does not exist.
            ValueError: If the JSON is malformed or missing required fields.
        """
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
        """Deserializes a single Smart Collection from a dict.

        Args:
            data: Dict with name, logic, rules, and optional metadata.

        Returns:
            SmartCollection instance ready for creation.

        Raises:
            ValueError: If required fields are missing or invalid.
            KeyError: If required fields are missing.
        """
        name = data.get("name", "").strip()
        if not name:
            msg = "Collection name is required"
            raise ValueError(msg)

        # Parse logic operator
        logic_str = data.get("logic", "OR")
        try:
            logic = LogicOperator(logic_str)
        except ValueError:
            logger.warning("Unknown logic '%s', defaulting to OR", logic_str)
            logic = LogicOperator.OR

        # Parse rules
        raw_rules = data.get("rules", [])
        if not isinstance(raw_rules, list):
            msg = "'rules' must be a list"
            raise ValueError(msg)

        rules = []
        for rule_data in raw_rules:
            rules.append(rule_from_dict(rule_data))

        return SmartCollection(
            name=name,
            description=data.get("description", ""),
            icon=data.get("icon", "\U0001f9e0"),
            logic=logic,
            rules=rules,
            auto_sync=data.get("auto_sync", True),
        )
