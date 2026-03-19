#
# steam_library_manager/utils/json_exporter.py
# Exports the game library to JSON format
#
# Copyright © 2025-2026 SwitchBros
# Licensed under the MIT License. See LICENSE for details.
#

import json
import logging

from steam_library_manager.utils.export_utils import game_to_export_dict, sorted_for_export

logger = logging.getLogger("steamlibmgr.json_exporter")

__all__ = ["JSONExporter"]


class JSONExporter:
    """Exports game lists as structured JSON files."""

    @staticmethod
    def export(games, output_path):
        # Serialize all games to a JSON file at output_path
        data = [game_to_export_dict(g) for g in sorted_for_export(games)]

        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as fh:
            json.dump({"games": data, "count": len(data)}, fh, indent=2, ensure_ascii=False)

        logger.info("Exported %d games (JSON) to %s", len(games), output_path)
