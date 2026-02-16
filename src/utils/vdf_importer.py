# src/utils/vdf_importer.py

"""VDF collection importer for Steam Library Manager.

Reads exported VDF text files and extracts collection data
(collection name + list of app IDs) for import into cloud storage.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import vdf

logger = logging.getLogger("steamlibmgr.vdf_importer")

__all__ = ["ImportedCollection", "VDFImporter"]


@dataclass(frozen=True)
class ImportedCollection:
    """A collection parsed from a VDF file.

    Attributes:
        name: The collection name.
        app_ids: Tuple of app IDs belonging to this collection.
    """

    name: str
    app_ids: tuple[int, ...] = field(default_factory=tuple)


class VDFImporter:
    """Imports collections from VDF text files."""

    @staticmethod
    def import_collections(file_path: Path) -> list[ImportedCollection]:
        """Reads a VDF text file and extracts collections.

        Expects VDF structure like:
            "collections" { "CollName" { "id" "..." "name" "..." "0" "440" "1" "570" } }

        Args:
            file_path: Path to the VDF file to import.

        Returns:
            List of ImportedCollection objects.

        Raises:
            FileNotFoundError: If the file does not exist.
            ValueError: If the VDF structure is invalid.
        """
        if not file_path.exists():
            raise FileNotFoundError(f"VDF file not found: {file_path}")

        with open(file_path, "r", encoding="utf-8") as fh:
            content = fh.read()

        try:
            data = vdf.loads(content)
        except Exception as exc:
            raise ValueError(f"Invalid VDF format: {exc}") from exc

        collections_data: dict[str, Any] = data.get("collections", {})
        if not collections_data:
            return []

        result: list[ImportedCollection] = []
        for _key, coll_data in collections_data.items():
            if not isinstance(coll_data, dict):
                continue

            name = coll_data.get("name", _key)
            app_ids: list[int] = []

            for k, v in coll_data.items():
                if k in ("id", "name", "count"):
                    continue
                try:
                    app_ids.append(int(v))
                except (ValueError, TypeError):
                    continue

            result.append(ImportedCollection(name=name, app_ids=tuple(app_ids)))

        logger.info("Imported %d collections from %s", len(result), file_path)
        return result
