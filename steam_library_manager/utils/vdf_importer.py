#
# steam_library_manager/utils/vdf_importer.py
# VDF collection importer for Steam Library Manager
#
# Copyright © 2025-2026 SwitchBros
# Licensed under the MIT License. See LICENSE for details.
#
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
    """A collection parsed from a VDF file."""

    name: str
    app_ids: tuple[int, ...] = field(default_factory=tuple)


class VDFImporter:
    """Imports collections from VDF text files."""

    @staticmethod
    def import_collections(file_path: Path) -> list[ImportedCollection]:
        """Read a VDF text file and extract collections."""
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
