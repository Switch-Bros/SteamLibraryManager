#
# steam_library_manager/utils/csv_exporter.py
# CSV export for game data (simple and full formats)
#
# Copyright © 2025-2026 SwitchBros
# Licensed under the MIT License. See LICENSE for details.
#
from __future__ import annotations

import csv
import logging
from collections.abc import Callable
from pathlib import Path
from typing import Any, TYPE_CHECKING

from steam_library_manager.utils.export_utils import game_to_export_dict, sorted_for_export

if TYPE_CHECKING:
    from steam_library_manager.core.game import Game

logger = logging.getLogger("steamlibmgr.csv_exporter")

__all__ = ["CSVExporter"]

_FULL_EXPORT_KEYS: tuple[str, ...] = (
    "name",
    "app_id",
    "sort_name",
    "developer",
    "publisher",
    "release_year",
    "genres",
    "tags",
    "categories",
    "platforms",
    "app_type",
    "playtime_hours",
    "last_played",
    "installed",
    "hidden",
    "proton_db_rating",
    "steam_deck_status",
    "review_percentage",
    "review_count",
    "hltb_main_story",
    "hltb_main_extras",
    "hltb_completionist",
)

_FULL_HEADERS: tuple[str, ...] = (
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
)


def _flatten_value(value: Any) -> Any:
    """Lists joined by '; ', None to empty string."""
    if isinstance(value, list):
        return "; ".join(str(v) for v in value)
    if value is None:
        return ""
    return value


class CSVExporter:
    """Exports game lists as CSV files in simple or full format."""

    @staticmethod
    def _export(
        games: list[Game],
        output_path: Path,
        headers: tuple[str, ...],
        row_fn: Callable[[Game], list[Any]],
    ) -> None:
        """Shared CSV export logic: mkdir, write header, sort, write rows."""
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", newline="", encoding="utf-8") as fh:
            writer = csv.writer(fh)
            writer.writerow(headers)
            for game in sorted_for_export(games):
                writer.writerow(row_fn(game))
        logger.info("Exported %d games to %s", len(games), output_path)

    @staticmethod
    def export_simple(games: list[Game], output_path: Path) -> None:
        """Export a simple CSV with Name, App ID, Playtime columns."""
        CSVExporter._export(
            games,
            output_path,
            ("Name", "App ID", "Playtime (hours)"),
            lambda g: [g.name, g.app_id, g.playtime_hours],
        )

    @staticmethod
    def export_full(games: list[Game], output_path: Path) -> None:
        """Export a full CSV with all available metadata."""

        def row_fn(game: Game) -> list[Any]:
            d = game_to_export_dict(game)
            return [_flatten_value(d[k]) for k in _FULL_EXPORT_KEYS]

        CSVExporter._export(games, output_path, _FULL_HEADERS, row_fn)
