#
# steam_library_manager/utils/vdf_exporter.py
# Exports category/collection data back to localconfig.vdf format
#
# Copyright © 2025-2026 SwitchBros
# Licensed under the MIT License. See LICENSE for details.
#

import logging

import vdf

logger = logging.getLogger("steamlibmgr.vdf_exporter")

__all__ = ["VDFTextExporter"]


class VDFTextExporter:
    """Dumps Steam collections into human-readable VDF text files
    using the vdf library's dumps() for correct Valve formatting.
    """

    @staticmethod
    def export_collections(collections, output_path):
        # Writes each collection dict (name, id, added) to a VDF file
        vdf_data = {"collections": {}}

        for idx, coll in enumerate(collections):
            name = coll.get("name", "Collection_%d" % idx)
            cid = coll.get("id", "coll_%d" % idx)
            added = coll.get("added", [])

            entry = {
                "id": cid,
                "name": name,
                "count": str(len(added)),
            }

            for app_idx, app_id in enumerate(added):
                entry[str(app_idx)] = str(app_id)

            vdf_data["collections"][name] = entry

        text = vdf.dumps(vdf_data, pretty=True)

        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as fh:
            fh.write(text)

        logger.info("Exported %d collections to %s", len(collections), output_path)
