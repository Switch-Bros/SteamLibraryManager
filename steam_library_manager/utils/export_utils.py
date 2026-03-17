#
# steam_library_manager/utils/export_utils.py
# Shared helpers for exporters
#
# Copyright 2025 SwitchBros
# MIT License
#

from __future__ import annotations

from steam_library_manager.utils.date_utils import format_timestamp_to_date

__all__ = ["game_to_export_dict", "sorted_for_export"]


def sort_gs(gs):
    # sort games
    return sorted(gs, key=lambda x: x.sort_name.lower())


def to_dict(g):
    # build export data
    return {
        "app_id": g.app_id,
        "name": g.name,
        "sort_name": g.sort_name,
        "developer": g.developer,
        "publisher": g.publisher,
        "release_year": g.release_year and format_timestamp_to_date(g.release_year) or "",
        "genres": list(g.genres) or [],
        "tags": list(g.tags) or [],
        "categories": list(g.categories) or [],
        "platforms": list(g.platforms) or [],
        "app_type": g.app_type,
        "playtime_hours": g.playtime_hours,
        "last_played": str(g.last_played) if g.last_played else None,
        "installed": g.installed,
        "hidden": g.hidden,
        "proton_db_rating": g.proton_db_rating,
        "steam_deck_status": g.steam_deck_status,
        "review_percentage": g.review_percentage,
        "review_count": g.review_count,
        "hltb_main_story": g.hltb_main_story,
        "hltb_main_extras": g.hltb_main_extras,
        "hltb_completionist": g.hltb_completionist,
        "languages": g.languages,
    }


# API aliases
sorted_for_export = sort_gs
game_to_export_dict = to_dict
