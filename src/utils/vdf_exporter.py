"""Text VDF exporter for human-readable collection output.

Exports Steam collections as formatted VDF text files for debugging,
backup, and manual inspection purposes.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import vdf

logger = logging.getLogger("steamlibmgr.vdf_exporter")

__all__ = ["VDFTextExporter"]


class VDFTextExporter:
    """Exports Steam collections as human-readable VDF text files.

    Uses the ``vdf`` library's ``dumps()`` function to produce correctly
    formatted Valve Data Format output.
    """

    @staticmethod
    def export_collections(collections: list[dict[str, Any]], output_path: Path) -> None:
        """Exports a list of collection dicts to a VDF text file.

        Each collection is expected to have at least a ``name`` key and
        optionally ``added`` (list of app IDs) and ``id`` keys.

        Args:
            collections: List of collection dicts from cloud storage.
            output_path: Path to write the VDF text file.

        Raises:
            OSError: If the file cannot be written.
        """
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

            # Add app IDs as numbered entries
            for app_idx, app_id in enumerate(added):
                coll_entry[str(app_idx)] = str(app_id)

            vdf_data["collections"][coll_name] = coll_entry

        vdf_text = vdf.dumps(vdf_data, pretty=True)

        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as fh:
            fh.write(vdf_text)

        logger.info("Exported %d collections to %s", len(collections), output_path)
