#
# steam_library_manager/integrations/hltb_models.py
# Data models for HowLongToBeat API responses
#
# Copyright © 2025-2026 SwitchBros
# Licensed under the MIT License. See LICENSE for details.
#

#
# steam_library_manager/integrations/hltb_models.py
# HLTB data models and name processing utilities
#
# Copyright © 2025-2026 SwitchBros
# Licensed under the MIT License. See LICENSE for details.
#

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

__all__ = [
    "HLTBResult",
    "find_best_match",
    "levenshtein",
    "normalize_for_compare",
    "normalize_name",
    "simplify_name",
    "to_result",
]


# HLTB result dataclass


@dataclass(frozen=True)
class HLTBResult:
    """Frozen dataclass for HowLongToBeat completion time data."""

    game_name: str
    main_story: float
    main_extras: float
    completionist: float


# Name processing constants

# Symbols to strip from game names (TM, (R), (C), also text forms)
# Uses a space replacement to avoid "Velocity(R)Ultra" -> "VelocityUltra"
_SYMBOL_PATTERN = re.compile(r"[\u2122\u00AE\u00A9]|\(TM\)|\(R\)")

# Superscript digits -> normal digits
_SUPERSCRIPT_MAP = str.maketrans("\u2070\u00b9\u00b2\u00b3\u2074\u2075\u2076\u2077\u2078\u2079", "0123456789")

# Bare year at end of name without parentheses: "Game 2014" -> "Game"
_BARE_YEAR_PATTERN = re.compile(r"\s+[12][09]\d\d$")

# Parenthetical noise to strip before search (year tags, Classic, etc.)
_PAREN_NOISE_PATTERN = re.compile(
    r"\s*\("
    r"(?:"
    r"[12][09]\d\d"  # Year: (2003), (1999), (2020)
    r"|Classic"  # (Classic)
    r"|CLASSIC"  # (CLASSIC)
    r"|Legacy"  # (Legacy)
    r"|\d+[Dd]\s*Remake"  # (3D Remake)
    r")\)"
    r"\s*",
)

# Edition/subtitle suffixes to strip for a fallback search.
# Inspired by hltb-millennium-plugin's simplify_game_name().
# Applied iteratively until no more changes.
_EDITION_PATTERNS: tuple[re.Pattern[str], ...] = (
    # Anniversary patterns (longer first)
    re.compile(r"\s+\d+[snrt][tdh]\s+Anniversary\s+Edition$", re.IGNORECASE),
    re.compile(r"\s+[-:\u2013\u2014]\s*Anniversary\s+Edition$", re.IGNORECASE),
    re.compile(r"\s+Anniversary\s+Edition$", re.IGNORECASE),
    # Edition suffixes (with optional dash/colon prefix)
    re.compile(
        r"\s+[-:\u2013\u2014]\s*("
        r"Enhanced|Complete|Definitive|Ultimate|Special|Legacy|Maximum|"
        r"Deluxe|Premium|Premium\s+Online|Gold|Platinum|Steam|"
        r"GOTY|Game\s+of\s+the\s+Year"
        r")\s*Edition.*$",
        re.IGNORECASE,
    ),
    re.compile(
        r"\s+("
        r"Enhanced|Complete|Definitive|Ultimate|Special|Legacy|Maximum|"
        r"Deluxe|Premium|Premium\s+Online|Gold|Platinum|Steam|"
        r"GOTY|Game\s+of\s+the\s+Year"
        r")\s*Edition.*$",
        re.IGNORECASE,
    ),
    # Standalone GOTY / Game of the Year
    re.compile(r"\s+[-:\u2013\u2014]\s*GOTY$", re.IGNORECASE),
    re.compile(r"\s+GOTY$", re.IGNORECASE),
    re.compile(r"\s+[-:\u2013\u2014]\s*Game\s+of\s+the\s+Year$", re.IGNORECASE),
    re.compile(r"\s+Game\s+of\s+the\s+Year$", re.IGNORECASE),
    # Remastered / Remake
    re.compile(r"\s+[-:\u2013\u2014]\s*Remastered$", re.IGNORECASE),
    re.compile(r"\s+Remastered$", re.IGNORECASE),
    re.compile(r"\s+\(\d*[Dd]\s*Remake\)$"),
    re.compile(r"\s+[-:\u2013\u2014]\s*Remake$", re.IGNORECASE),
    re.compile(r"\s+Remake$", re.IGNORECASE),
    # Director's Cut
    re.compile(r"\s+[-:\u2013\u2014]\s*Director'?s?\s+Cut$", re.IGNORECASE),
    re.compile(r"\s+Director'?s?\s+Cut$", re.IGNORECASE),
    # Collection / Classic / HD / Enhanced standalone
    re.compile(r"\s+Collection$", re.IGNORECASE),
    re.compile(r"\s+\(Legacy\)$", re.IGNORECASE),
    re.compile(r"\s+[-:\u2013\u2014]\s*Classic$", re.IGNORECASE),
    re.compile(r"\s+Classic$", re.IGNORECASE),
    re.compile(r"\s+\(CLASSIC\)$"),
    re.compile(r"\s+HD$", re.IGNORECASE),
    re.compile(r"\s+Enhanced$", re.IGNORECASE),
    re.compile(r"\s+Redux$", re.IGNORECASE),
    re.compile(r"\s+Reloaded$", re.IGNORECASE),
    # Single Player / Online / Season N
    re.compile(r"\s+[-:\u2013\u2014]\s*Single\s+Player$", re.IGNORECASE),
    re.compile(r"\s+Single\s+Player$", re.IGNORECASE),
    re.compile(r"\s+[-:\u2013\u2014]\s*Season\s+\d+$", re.IGNORECASE),
    re.compile(r"\s+Season\s+\d+$", re.IGNORECASE),
    re.compile(r"\s+Online$", re.IGNORECASE),
    # Year tags at end: (2013), (2020), etc.
    re.compile(r"\s+\([12][09]\d\d\)$"),
    # Clean up trailing punctuation left after stripping
    re.compile(r"\s*[-:\u2013\u2014]\s*$"),
)


# Name processing functions


def normalize_name(name: str) -> str:
    """Strips trademark and copyright symbols for cleaner search terms."""
    # Replace symbols with space (keeps word boundaries: "Velocity(R)Ultra" -> "Velocity Ultra")
    cleaned = _SYMBOL_PATTERN.sub(" ", name).strip()
    # Normalize superscript digits
    cleaned = cleaned.translate(_SUPERSCRIPT_MAP)
    # Normalize backtick to apostrophe
    cleaned = cleaned.replace("`", "'")
    # Strip special unicode chars
    cleaned = re.sub(r"[\u221e]", "", cleaned)
    # Strip parenthetical noise: (2003), (Classic), etc.
    cleaned = _PAREN_NOISE_PATTERN.sub("", cleaned).strip()
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned


def simplify_name(name: str) -> str:
    """Strips common edition/remaster/year suffixes for fallback search."""
    # Normalize Unicode dashes to ASCII hyphen with spaces for pattern matching
    name = re.sub(r"[\u2013\u2014]", " - ", name)
    name = re.sub(r"\s+", " ", name).strip()

    prev = ""
    while prev != name:
        prev = name
        for pattern in _EDITION_PATTERNS:
            name = pattern.sub("", name).strip()
        # Also strip bare year at end: "Lords Of The Fallen 2014" -> "Lords Of The Fallen"
        name = _BARE_YEAR_PATTERN.sub("", name).strip()
    return re.sub(r"\s+", " ", name).strip()


def normalize_for_compare(name: str) -> str:
    """Normalizes a name for comparison (lowercase, no accents, no special chars)."""
    result = name.lower()
    result = unicodedata.normalize("NFD", result)
    result = re.sub(r"[\u0300-\u036f]", "", result)
    result = re.sub(r"[^a-z0-9\s\-/]", "", result)
    return result.strip()


def levenshtein(s1: str, s2: str) -> int:
    """Calculates the Levenshtein (edit) distance between two strings."""
    if s1 == s2:
        return 0
    len1, len2 = len(s1), len(s2)
    if len1 == 0:
        return len2
    if len2 == 0:
        return len1

    # Use two-row optimization for O(min(m,n)) space
    if len1 > len2:
        s1, s2 = s2, s1
        len1, len2 = len2, len1

    prev_row = list(range(len1 + 1))
    for j in range(1, len2 + 1):
        curr_row = [j] + [0] * len1
        for i in range(1, len1 + 1):
            cost = 0 if s1[i - 1] == s2[j - 1] else 1
            curr_row[i] = min(
                curr_row[i - 1] + 1,  # insertion
                prev_row[i] + 1,  # deletion
                prev_row[i - 1] + cost,  # substitution
            )
        prev_row = curr_row

    return prev_row[len1]


def find_best_match(
    results: list[dict],
    search_name: str,
) -> tuple[dict | None, int]:
    """Finds the best matching game from HLTB search results."""
    sanitized_query = normalize_for_compare(search_name)

    # Exact name match
    for r in results:
        if normalize_for_compare(r.get("game_name", "")) == sanitized_query:
            return r, 0

    # Levenshtein distance with popularity tiebreaker
    candidates: list[tuple[int, int, dict]] = []
    for r in results:
        r_name = normalize_for_compare(r.get("game_name", ""))
        dist = levenshtein(sanitized_query, r_name)
        popularity = r.get("comp_all_count", 0)
        candidates.append((dist, -popularity, r))

    if not candidates:
        return None, 0

    # Sort by distance ASC, then by popularity DESC (negative = more popular first)
    candidates.sort(key=lambda c: (c[0], c[1]))
    best_dist, _, best_match = candidates[0]

    return best_match, best_dist


def to_result(match: dict) -> HLTBResult:
    """Converts an HLTB API result dict to an HLTBResult."""
    return HLTBResult(
        game_name=match.get("game_name", ""),
        main_story=match.get("comp_main", 0) / 3600,
        main_extras=match.get("comp_plus", 0) / 3600,
        completionist=match.get("comp_100", 0) / 3600,
    )
