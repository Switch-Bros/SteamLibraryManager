#
# steam_library_manager/utils/name_utils.py
# Name modification utilities for game metadata
#
# Copyright (c) 2025-2026 SwitchBros
# Licensed under the MIT License. See LICENSE for details.
#

from __future__ import annotations

__all__ = ["apply_name_modifications"]


def apply_name_modifications(name: str, mods: dict[str, str]) -> str:
    """Apply prefix, suffix, and remove mods to a game name.

    Order: remove first, then prefix, then suffix.
    """
    result = name
    if mods.get("remove"):
        result = result.replace(mods["remove"], "")
    if mods.get("prefix"):
        result = mods["prefix"] + result
    if mods.get("suffix"):
        result = result + mods["suffix"]
    return result
