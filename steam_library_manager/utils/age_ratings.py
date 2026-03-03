"""Age rating conversion utilities.

Single source of truth for all rating system conversions.
Replaces duplicated maps in steam_store.py, game_detail_service.py,
and game_details_widget.py.
"""

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
    """Convert any rating system to PEGI equivalent.

    Args:
        rating: The rating value (e.g., "everyone", "12", "T").
        system: The rating system (e.g., "esrb", "usk", "cero").

    Returns:
        PEGI equivalent string, or None if no mapping exists.
    """
    maps = {"usk": USK_TO_PEGI, "esrb": ESRB_TO_PEGI, "cero": CERO_TO_PEGI}
    return maps.get(system.lower(), {}).get(rating.lower())
