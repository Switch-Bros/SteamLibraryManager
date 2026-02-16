# src/utils/csv_exporter.py

"""CSV export utilities for game data.

Provides simple (name + playtime) and full (all metadata) CSV export
formats for the Steam Library Manager.
"""

from __future__ import annotations

import csv
import logging
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.core.game import Game

logger = logging.getLogger("steamlibmgr.csv_exporter")

__all__ = ["CSVExporter"]


class CSVExporter:
    """Exports game lists as CSV files in two formats.

    Simple format: Name, App ID, Playtime (hours)
    Full format: All available metadata fields
    """

    @staticmethod
    def export_simple(games: list[Game], output_path: Path) -> None:
        """Exports a simple CSV with basic game info.

        Columns: Name, App ID, Playtime (hours)

        Args:
            games: List of games to export.
            output_path: Path to write the CSV file.

        Raises:
            OSError: If the file cannot be written.
        """
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", newline="", encoding="utf-8") as fh:
            writer = csv.writer(fh)
            writer.writerow(["Name", "App ID", "Playtime (hours)"])
            for game in sorted(games, key=lambda g: g.sort_name.lower()):
                writer.writerow([game.name, game.app_id, game.playtime_hours])

        logger.info("Exported %d games (simple) to %s", len(games), output_path)

    @staticmethod
    def export_full(games: list[Game], output_path: Path) -> None:
        """Exports a full CSV with all available metadata.

        Columns: Name, App ID, Sort Name, Developer, Publisher, Release Year,
                 Genres, Tags, Categories, Platforms, App Type, Playtime (hours),
                 Last Played, Installed, Hidden, ProtonDB, Steam Deck,
                 Review Score, Review Count, HLTB Main, HLTB Main+Extras,
                 HLTB Completionist

        Args:
            games: List of games to export.
            output_path: Path to write the CSV file.

        Raises:
            OSError: If the file cannot be written.
        """
        headers = [
            "Name",
            "App ID",
            "Sort Name",
            "Developer",
            "Publisher",
            "Release Year",
            "Genres",
            "Tags",
            "Categories",
            "Platforms",
            "App Type",
            "Playtime (hours)",
            "Last Played",
            "Installed",
            "Hidden",
            "ProtonDB",
            "Steam Deck",
            "Review Score",
            "Review Count",
            "HLTB Main (hours)",
            "HLTB Main+Extras (hours)",
            "HLTB Completionist (hours)",
        ]

        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", newline="", encoding="utf-8") as fh:
            writer = csv.writer(fh)
            writer.writerow(headers)
            for game in sorted(games, key=lambda g: g.sort_name.lower()):
                writer.writerow(
                    [
                        game.name,
                        game.app_id,
                        game.sort_name,
                        game.developer,
                        game.publisher,
                        game.release_year,
                        "; ".join(game.genres),
                        "; ".join(game.tags),
                        "; ".join(game.categories),
                        "; ".join(game.platforms),
                        game.app_type,
                        game.playtime_hours,
                        str(game.last_played) if game.last_played else "",
                        game.installed,
                        game.hidden,
                        game.proton_db_rating,
                        game.steam_deck_status,
                        game.review_percentage,
                        game.review_count,
                        game.hltb_main_story,
                        game.hltb_main_extras,
                        game.hltb_completionist,
                    ]
                )

        logger.info("Exported %d games (full) to %s", len(games), output_path)
