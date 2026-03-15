# steam_library_manager/ui/constants.py

"""Shared UI constants and helpers.

Centralizes definitions that multiple UI handlers and widgets depend on,
such as the set of protected (non-editable) collection names.
"""

from __future__ import annotations

from steam_library_manager.utils.i18n import t

__all__ = ["get_protected_collection_names"]


def get_protected_collection_names() -> set[str]:
    """Returns the set of built-in collection names that cannot be modified.

    Called at runtime so that translated names reflect the active locale.
    Includes Steam-internal names (lowercase English) which may appear
    when collections come from Depressurizer or raw cloud storage.
    """
    return {
        t("categories.all_games"),
        t("categories.favorites"),
        t("categories.uncategorized"),
        t("categories.hidden"),
        # Steam-internal names (lowercase, used by Depressurizer and raw cloud storage)
        "favorite",
        "hidden",
    }
