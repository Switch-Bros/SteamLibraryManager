# src/utils/json_exporter.py

"""JSON export utility for game data.

Exports the full game library as a structured JSON file for backup,
analysis, or interoperability with other tools.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, TYPE_CHECKING

from src.utils.export_utils import game_to_export_dict, sorted_for_export

if TYPE_CHECKING:
    from src.core.game import Game

logger = logging.getLogger("steamlibmgr.json_exporter")

__all__ = ["JSONExporter"]


class JSONExporter:
    """Exports game lists as structured JSON files."""

    @staticmethod
    def export(games: list[Game], output_path: Path) -> None:
        """Exports game data as a JSON file.

        Each game is serialized as a dictionary with all available metadata.

        Args:
            games: List of games to export.
            output_path: Path to write the JSON file.

        Raises:
            OSError: If the file cannot be written.
        """
        data: list[dict[str, Any]] = [game_to_export_dict(game) for game in sorted_for_export(games)]

        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as fh:
            json.dump({"games": data, "count": len(data)}, fh, indent=2, ensure_ascii=False)

        logger.info("Exported %d games (JSON) to %s", len(games), output_path)
