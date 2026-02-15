"""HowLongToBeat API client for game completion time data.

Wraps the howlongtobeatpy library to search for games and return
normalized completion time data as frozen dataclasses.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass

logger = logging.getLogger("steamlibmgr.hltb_api")

__all__ = ["HLTBClient", "HLTBResult"]


@dataclass(frozen=True)
class HLTBResult:
    """Frozen dataclass for HowLongToBeat completion time data.

    Attributes:
        game_name: Name of the game as returned by HLTB.
        main_story: Hours to complete the main story.
        main_extras: Hours to complete main story + extras.
        completionist: Hours for 100% completion.
    """

    game_name: str
    main_story: float
    main_extras: float
    completionist: float


# Pattern to strip common name noise for better HLTB matching
_STRIP_PATTERN = re.compile(
    r"[\u2122\u00AE]"  # TM, (R) symbols
    r"|[-\u2013\u2014]\s*(Deluxe|Ultimate|Gold|GOTY|Complete|Definitive|Enhanced|"
    r"Remastered|Anniversary|Legendary|Premium|Special)\s*Edition.*$",
    re.IGNORECASE,
)


class HLTBClient:
    """Client for searching HowLongToBeat game data.

    Uses the howlongtobeatpy library for search. Falls back gracefully
    if the library is not installed.
    """

    @staticmethod
    def is_available() -> bool:
        """Checks whether the howlongtobeatpy library is installed.

        Returns:
            True if howlongtobeatpy can be imported.
        """
        try:
            from howlongtobeatpy import HowLongToBeat  # noqa: F401

            return True
        except ImportError:
            return False

    def search_game(self, name: str) -> HLTBResult | None:
        """Searches HLTB for a game and returns the best match.

        Args:
            name: Game name to search for. Will be normalized before search.

        Returns:
            HLTBResult with completion times, or None if not found
            or if the library is not installed.
        """
        try:
            from howlongtobeatpy import HowLongToBeat
        except ImportError:
            logger.warning("howlongtobeatpy not installed")
            return None

        normalized = self._normalize_name(name)
        if not normalized:
            return None

        try:
            results = HowLongToBeat().search(normalized)
        except Exception as exc:
            logger.warning("HLTB search failed for '%s': %s", normalized, exc)
            return None

        if not results:
            return None

        # Pick best match (highest similarity)
        best = max(results, key=lambda r: r.similarity)

        return HLTBResult(
            game_name=best.game_name,
            main_story=best.main_story or 0.0,
            main_extras=best.main_extra or 0.0,
            completionist=best.completionist or 0.0,
        )

    @staticmethod
    def _normalize_name(name: str) -> str:
        """Strips trademark symbols and edition suffixes for better matching.

        Args:
            name: Raw game name.

        Returns:
            Cleaned name suitable for HLTB search.
        """
        cleaned = _STRIP_PATTERN.sub("", name).strip()
        # Collapse multiple spaces
        cleaned = re.sub(r"\s+", " ", cleaned)
        return cleaned
