#
# steam_library_manager/utils/vdf_importer.py
# Imports and normalizes VDF collection data into internal models
#
# Copyright © 2025-2026 SwitchBros
# Licensed under the MIT License. See LICENSE for details.
#

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path

import vdf

logger = logging.getLogger("steamlibmgr.vdf_importer")

__all__ = ["ImportedCollection", "VDFImporter"]

# metadata keys we skip when pulling app IDs
_SKIP = {"id", "name", "count"}


@dataclass(frozen=True)
class ImportedCollection:
    """A collection parsed from a VDF file."""

    name: str
    app_ids: tuple[int, ...] = field(default_factory=tuple)


class VDFImporter:
    # imports collections from VDF text files

    @staticmethod
    def import_collections(fp: Path) -> list[ImportedCollection]:
        # read file and pull out every collection block
        # expected layout: "collections" { "Name" { "id" "..." "0" "440" } }
        if not fp.exists():
            raise FileNotFoundError("VDF file not found: %s" % fp)

        with open(fp, "r", encoding="utf-8") as fh:
            content = fh.read()

        try:
            data = vdf.loads(content)
        except Exception as exc:
            raise ValueError("Invalid VDF format: %s" % exc) from exc

        colls = data.get("collections", {})
        if not colls:
            return []

        res = []

        for key, cd in colls.items():
            if not isinstance(cd, dict):
                continue

            nm = cd.get("name", key)

            # grab every value whose key isn't reserved
            ids = []
            for k, v in cd.items():
                if k in _SKIP:
                    continue
                try:
                    ids.append(int(v))
                except (ValueError, TypeError):
                    continue

            res.append(ImportedCollection(name=nm, app_ids=tuple(ids)))

        logger.info("Imported %d collections from %s" % (len(res), fp))
        return res
