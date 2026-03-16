#
# steam_library_manager/ui/constants.py
# Shared UI constants (protected collection names, etc.)
#
# Copyright © 2025-2026 SwitchBros
# Licensed under the MIT License. See LICENSE for details.
#

from __future__ import annotations

from steam_library_manager.utils.i18n import t

__all__ = ["get_protected_collection_names"]


def get_protected_collection_names() -> set[str]:
    """Returns built-in collection names that cannot be modified."""
    return {
        t("categories.all_games"),
        t("categories.favorites"),
        t("categories.uncategorized"),
        t("categories.hidden"),
        "favorite",
        "hidden",
    }
