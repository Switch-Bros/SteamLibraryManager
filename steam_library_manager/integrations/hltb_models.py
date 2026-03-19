#
# steam_library_manager/integrations/hltb_models.py
# Data models for HowLongToBeat API responses
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


@dataclass(frozen=True)
class HLTBResult:
    """HLTB completion time data for one game."""

    game_name: str
    main_story: float
    main_extras: float
    completionist: float


# Symbols to strip (TM, (R), (C)) - space replacement keeps word boundaries
_SYM_RE = re.compile(r"[\u2122\u00AE\u00A9]|\(TM\)|\(R\)")

# Superscript digits -> normal digits
_SUP_MAP = str.maketrans("\u2070\u00b9\u00b2\u00b3\u2074\u2075\u2076\u2077\u2078\u2079", "0123456789")

# Bare year at end: "Game 2014" -> "Game"
_BARE_YEAR_RE = re.compile(r"\s+[12][09]\d\d$")

# Parenthetical noise: (2003), (Classic), (Legacy), (3D Remake)
_PAREN_NOISE_RE = re.compile(
    r"\s*\(" r"(?:" r"[12][09]\d\d" r"|Classic" r"|CLASSIC" r"|Legacy" r"|\d+[Dd]\s*Remake" r")\)" r"\s*",
)

# Edition/subtitle suffixes stripped iteratively for fallback search
_EDITION_RES = (
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
    # Trailing punctuation left after stripping
    re.compile(r"\s*[-:\u2013\u2014]\s*$"),
)


def normalize_name(name):
    # Strip TM/copyright symbols, superscripts, parenthetical noise
    out = _SYM_RE.sub(" ", name).strip()
    out = out.translate(_SUP_MAP)
    out = out.replace("`", "'")
    out = re.sub(r"[\u221e]", "", out)
    out = _PAREN_NOISE_RE.sub("", out).strip()
    out = re.sub(r"\s+", " ", out)
    return out


def simplify_name(name):
    # Strip edition/remaster/year suffixes for fallback search
    name = re.sub(r"[\u2013\u2014]", " - ", name)
    name = re.sub(r"\s+", " ", name).strip()

    prev = ""
    while prev != name:
        prev = name
        for pat in _EDITION_RES:
            name = pat.sub("", name).strip()
        name = _BARE_YEAR_RE.sub("", name).strip()
    return re.sub(r"\s+", " ", name).strip()


def normalize_for_compare(name):
    # Lowercase, strip accents, keep only [a-z0-9 -/]
    out = name.lower()
    out = unicodedata.normalize("NFD", out)
    out = re.sub(r"[\u0300-\u036f]", "", out)
    out = re.sub(r"[^a-z0-9\s\-/]", "", out)
    return out.strip()


def levenshtein(s1, s2):
    # Edit distance between two strings (two-row optimization)
    if s1 == s2:
        return 0
    n1, n2 = len(s1), len(s2)
    if n1 == 0:
        return n2
    if n2 == 0:
        return n1

    if n1 > n2:
        s1, s2 = s2, s1
        n1, n2 = n2, n1

    prev = list(range(n1 + 1))
    for j in range(1, n2 + 1):
        cur = [j] + [0] * n1
        for i in range(1, n1 + 1):
            cost = 0 if s1[i - 1] == s2[j - 1] else 1
            cur[i] = min(
                cur[i - 1] + 1,
                prev[i] + 1,
                prev[i - 1] + cost,
            )
        prev = cur

    return prev[n1]


def find_best_match(results, search_name):
    # Pick the closest HLTB result by name, with popularity tiebreaker
    query = normalize_for_compare(search_name)

    # Exact match first
    for r in results:
        if normalize_for_compare(r.get("game_name", "")) == query:
            return r, 0

    # Levenshtein with popularity tiebreaker
    cands = []
    for r in results:
        rn = normalize_for_compare(r.get("game_name", ""))
        dist = levenshtein(query, rn)
        pop = r.get("comp_all_count", 0)
        cands.append((dist, -pop, r))

    if not cands:
        return None, 0

    # Sort: distance ASC, popularity DESC
    cands.sort(key=lambda c: (c[0], c[1]))
    best_dist, _, best = cands[0]

    return best, best_dist


def to_result(match):
    # Convert raw HLTB API dict to HLTBResult (seconds -> hours)
    return HLTBResult(
        game_name=match.get("game_name", ""),
        main_story=match.get("comp_main", 0) / 3600,
        main_extras=match.get("comp_plus", 0) / 3600,
        completionist=match.get("comp_100", 0) / 3600,
    )
