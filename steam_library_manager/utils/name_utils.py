#
# steam_library_manager/utils/name_utils.py
# Game name normalization and fuzzy-matching utilities
#
# Copyright © 2025-2026 SwitchBros
# Licensed under the MIT License. See LICENSE for details.
#

from __future__ import annotations

__all__ = ["apply_name_modifications"]


def apply_name_modifications(name, mods):
    # Apply prefix, suffix, remove mods to a game name.
    # Order: remove -> prefix -> suffix
    out = name
    if mods.get("remove"):
        out = out.replace(mods["remove"], "")
    if mods.get("prefix"):
        out = mods["prefix"] + out
    if mods.get("suffix"):
        out = out + mods["suffix"]
    return out
