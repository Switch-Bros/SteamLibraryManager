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
        data: list[dict[str, Any]] = []
        for game in sorted(games, key=lambda g: g.sort_name.lower()):
            data.append(
                {
                    "app_id": game.app_id,
                    "name": game.name,
                    "sort_name": game.sort_name,
                    "developer": game.developer,
                    "publisher": game.publisher,
                    "release_year": game.release_year,
                    "genres": game.genres,
                    "tags": game.tags,
                    "categories": game.categories,
                    "platforms": game.platforms,
                    "app_type": game.app_type,
                    "playtime_hours": game.playtime_hours,
                    "last_played": str(game.last_played) if game.last_played else None,
                    "installed": game.installed,
                    "hidden": game.hidden,
                    "proton_db_rating": game.proton_db_rating,
                    "steam_deck_status": game.steam_deck_status,
                    "review_percentage": game.review_percentage,
                    "review_count": game.review_count,
                    "hltb_main_story": game.hltb_main_story,
                    "hltb_main_extras": game.hltb_main_extras,
                    "hltb_completionist": game.hltb_completionist,
                    "languages": game.languages,
                }
            )

        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as fh:
            json.dump({"games": data, "count": len(data)}, fh, indent=2, ensure_ascii=False)

        logger.info("Exported %d games (JSON) to %s", len(games), output_path)
