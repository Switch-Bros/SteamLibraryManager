# src/utils/name_utils.py

"""Name modification utilities for game metadata.

Shared by MetadataService (actual application) and MetadataDialogs (preview).
"""

from __future__ import annotations

__all__ = ["apply_name_modifications"]


def apply_name_modifications(name: str, mods: dict[str, str]) -> str:
    """Applies prefix, suffix, and remove modifications to a game name.

    Order: remove first (so prefix/suffix don't get mangled),
    then prefix, then suffix.

    Args:
        name: Original game name.
        mods: Dict with optional ``prefix``, ``suffix``, ``remove`` keys.

    Returns:
        Modified name string.
    """
    result = name
    if mods.get("remove"):
        result = result.replace(mods["remove"], "")
    if mods.get("prefix"):
        result = mods["prefix"] + result
    if mods.get("suffix"):
        result = result + mods["suffix"]
    return result
