#
# steam_library_manager/utils/export_utils.py
# Shared helpers for CSV, JSON, and other export formats
#
# Copyright (c) 2025-2026 SwitchBros
# Licensed under the MIT License. See LICENSE for details.
#

from __future__ import annotations

from typing import Any, TYPE_CHECKING

from steam_library_manager.utils.date_utils import format_timestamp_to_date

if TYPE_CHECKING:
    from steam_library_manager.core.game import Game

__all__ = ["game_to_export_dict", "sorted_for_export"]


def sorted_for_export(games: list[Game]) -> list[Game]:
    """Sorts games by sort_name for consistent export order."""
    return sorted(games, key=lambda g: g.sort_name.lower())


def game_to_export_dict(game: Game) -> dict[str, Any]:
    """Converts a Game to a standardized export dictionary."""
    return {
        "app_id": game.app_id,
        "name": game.name,
        "sort_name": game.sort_name,
        "developer": game.developer,
        "publisher": game.publisher,
        "release_year": format_timestamp_to_date(game.release_year) if game.release_year else "",
        "genres": list(game.genres) if game.genres else [],
        "tags": list(game.tags) if game.tags else [],
        "categories": list(game.categories) if game.categories else [],
        "platforms": list(game.platforms) if game.platforms else [],
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
