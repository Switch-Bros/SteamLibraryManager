#
# steam_library_manager/utils/vdf_exporter.py
# VDF text export for Steam collections
#
# Copyright © 2025-2026 SwitchBros
# Licensed under the MIT License. See LICENSE for details.
#
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import vdf

logger = logging.getLogger("steamlibmgr.vdf_exporter")

__all__ = ["VDFTextExporter"]


class VDFTextExporter:
    """Exports Steam collections as human-readable VDF text files."""

    @staticmethod
    def export_collections(collections: list[dict[str, Any]], output_path: Path) -> None:
        """Export a list of collection dicts to a VDF text file."""
        vdf_data: dict[str, Any] = {"collections": {}}

        for idx, coll in enumerate(collections):
            coll_name = coll.get("name", f"Collection_{idx}")
            coll_id = coll.get("id", f"coll_{idx}")
            added = coll.get("added", [])

            coll_entry: dict[str, Any] = {
                "id": coll_id,
                "name": coll_name,
                "count": str(len(added)),
            }

            for app_idx, app_id in enumerate(added):
                coll_entry[str(app_idx)] = str(app_id)

            vdf_data["collections"][coll_name] = coll_entry

        vdf_text = vdf.dumps(vdf_data, pretty=True)

        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as fh:
            fh.write(vdf_text)

        logger.info("Exported %d collections to %s", len(collections), output_path)
