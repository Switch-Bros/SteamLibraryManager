#
# steam_library_manager/utils/age_ratings.py
# Age rating conversion utilities (USK, ESRB, CERO -> PEGI)
#
# Copyright © 2025-2026 SwitchBros
# Licensed under the MIT License. See LICENSE for details.
#

from __future__ import annotations

__all__ = ["USK_TO_PEGI", "ESRB_TO_PEGI", "CERO_TO_PEGI", "convert_to_pegi"]

USK_TO_PEGI: dict[str, str] = {
    "0": "3",
    "6": "7",
    "12": "12",
    "16": "16",
    "18": "18",
}

ESRB_TO_PEGI: dict[str, str] = {
    # Full names
    "everyone": "3",
    "everyone 10+": "7",
    "e10+": "7",
    "teen": "12",
    "mature": "18",
    "mature 17+": "18",
    "adults only": "18",
    "adults only 18+": "18",
    # Short forms from appinfo.vdf
    "e": "3",
    "t": "12",
    "m": "18",
    "ao": "18",
}

CERO_TO_PEGI: dict[str, str] = {
    "A": "3",
    "B": "12",
    "C": "15",
    "D": "17",
    "Z": "18",
}


def convert_to_pegi(rating: str, system: str) -> str | None:
    """Convert any rating system to PEGI equivalent, or None if unmapped."""
    maps = {"usk": USK_TO_PEGI, "esrb": ESRB_TO_PEGI, "cero": CERO_TO_PEGI}
    return maps.get(system.lower(), {}).get(rating.lower())
