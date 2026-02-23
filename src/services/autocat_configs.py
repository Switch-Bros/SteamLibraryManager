"""Configuration dataclasses and constants for auto-categorization.

Defines AutoCatMethodConfig and BucketConfig for the two generic engines
in AutoCategorizeService, plus franchise detection constants.
"""

from __future__ import annotations

from dataclasses import dataclass

__all__ = [
    "AutoCatMethodConfig",
    "BucketConfig",
    "BUCKET_METHOD_CONFIGS",
    "GHOST_PREFIXES",
    "KNOWN_FRANCHISES",
    "SIMPLE_METHOD_CONFIGS",
]


@dataclass(frozen=True)
class AutoCatMethodConfig:
    """Configuration for a simple attribute-based categorization method.

    Args:
        attr: Game attribute name to read via getattr.
        i18n_key: Translation key for the category name.
        is_list: True if the attribute returns a list of values.
        use_raw: True if the value itself is the category name (no i18n wrapping).
        capitalize: True to capitalize the value before use.
        i18n_kwarg: Keyword argument name for the i18n key.
    """

    attr: str
    i18n_key: str = ""
    is_list: bool = False
    use_raw: bool = False
    capitalize: bool = False
    i18n_kwarg: str = "name"


@dataclass(frozen=True)
class BucketConfig:
    """Configuration for a threshold-based bucket categorization method.

    Args:
        attr: Game attribute name to read via getattr.
        buckets: Threshold/i18n-key pairs in DESCENDING order.
        i18n_wrapper_key: Translation key wrapping the bucket label.
        i18n_wrapper_kwarg: Keyword argument name for the wrapper key.
        fallback_key: Translation key for the no-data/zero-value bucket.
        skip_falsy: True to skip games with falsy attribute values.
    """

    attr: str
    buckets: tuple[tuple[int | float, str], ...]
    i18n_wrapper_key: str
    i18n_wrapper_kwarg: str = "name"
    fallback_key: str = ""
    skip_falsy: bool = True


# ---------------------------------------------------------------------------
# Simple method configurations
# ---------------------------------------------------------------------------

SIMPLE_METHOD_CONFIGS: dict[str, AutoCatMethodConfig] = {
    "publisher": AutoCatMethodConfig(
        attr="publisher",
        i18n_key="auto_categorize.cat_publisher",
    ),
    "developer": AutoCatMethodConfig(
        attr="developer",
        i18n_key="auto_categorize.cat_developer",
    ),
    "genre": AutoCatMethodConfig(
        attr="genres",
        is_list=True,
        use_raw=True,
    ),
    "platform": AutoCatMethodConfig(
        attr="platforms",
        i18n_key="auto_categorize.cat_platform",
        is_list=True,
        capitalize=True,
    ),
    "year": AutoCatMethodConfig(
        attr="release_year",
        i18n_key="auto_categorize.cat_year",
        i18n_kwarg="year",
    ),
    "language": AutoCatMethodConfig(
        attr="languages",
        i18n_key="auto_categorize.cat_language",
        is_list=True,
    ),
    "vr": AutoCatMethodConfig(
        attr="vr_support",
        i18n_key="auto_categorize.cat_vr",
        capitalize=True,
    ),
}

# ---------------------------------------------------------------------------
# Bucket method configurations
# ---------------------------------------------------------------------------

BUCKET_METHOD_CONFIGS: dict[str, BucketConfig] = {
    "user_score": BucketConfig(
        attr="review_percentage",
        buckets=(
            (95, "ui.reviews.overwhelmingly_positive"),
            (80, "ui.reviews.very_positive"),
            (70, "ui.reviews.positive"),
            (40, "ui.reviews.mixed"),
            (0, "ui.reviews.negative"),
        ),
        i18n_wrapper_key="auto_categorize.cat_user_score",
        skip_falsy=True,
    ),
    "hours_played": BucketConfig(
        attr="playtime_minutes",
        buckets=(
            (6001, "auto_categorize.hours_100_plus"),
            (3001, "auto_categorize.hours_50_100"),
            (601, "auto_categorize.hours_10_50"),
            (121, "auto_categorize.hours_2_10"),
            (1, "auto_categorize.hours_0_2"),
        ),
        i18n_wrapper_key="auto_categorize.cat_hours_played",
        i18n_wrapper_kwarg="range",
        fallback_key="auto_categorize.hours_never",
        skip_falsy=False,
    ),
    "hltb": BucketConfig(
        attr="hltb_main_story",
        buckets=(
            (50, "auto_categorize.hltb_50_plus"),
            (30, "auto_categorize.hltb_30_50"),
            (15, "auto_categorize.hltb_15_30"),
            (5, "auto_categorize.hltb_5_15"),
            (0.1, "auto_categorize.hltb_under_5"),
        ),
        i18n_wrapper_key="auto_categorize.cat_hltb",
        i18n_wrapper_kwarg="range",
        skip_falsy=True,
    ),
}

# ---------------------------------------------------------------------------
# Franchise detection constants
# ---------------------------------------------------------------------------

# Well-known gaming franchises for auto-categorization.
# Only these (or franchises with 2+ games detected) create categories.
KNOWN_FRANCHISES: frozenset[str] = frozenset(
    {
        "Age of Empires",
        "Anno",
        "Arma",
        "Assassin's Creed",
        "Baldur's Gate",
        "Batman",
        "Battlefield",
        "BioShock",
        "Borderlands",
        "Call of Duty",
        "Castlevania",
        "Civilization",
        "Command & Conquer",
        "Counter-Strike",
        "Crusader Kings",
        "Crysis",
        "Dark Souls",
        "Darksiders",
        "Dead Space",
        "Deus Ex",
        "Devil May Cry",
        "Diablo",
        "Dishonored",
        "Divinity",
        "DOOM",
        "Dragon Age",
        "Dragon Quest",
        "Dying Light",
        "Europa Universalis",
        "Fallout",
        "Far Cry",
        "Final Fantasy",
        "Gears of War",
        "Grand Theft Auto",
        "Half-Life",
        "Halo",
        "Hearts of Iron",
        "Hitman",
        "Hollow Knight",
        "Just Cause",
        "King's Bounty",
        "LEGO",
        "Left 4 Dead",
        "Mafia",
        "Mass Effect",
        "Max Payne",
        "Mega Man",
        "Metal Gear",
        "Metro",
        "Middle-earth",
        "Monster Hunter",
        "Mortal Kombat",
        "Need for Speed",
        "Ori",
        "Pathfinder",
        "Payday",
        "Persona",
        "Pillars of Eternity",
        "Portal",
        "Prince of Persia",
        "Quake",
        "Rainbow Six",
        "Red Dead",
        "Resident Evil",
        "Saints Row",
        "Sid Meier's Civilization",
        "Silent Hill",
        "Sniper Elite",
        "Sonic",
        "South Park",
        "Splinter Cell",
        "S.T.A.L.K.E.R.",
        "StarCraft",
        "Star Wars",
        "SteamWorld",
        "Street Fighter",
        "System Shock",
        "Tekken",
        "The Elder Scrolls",
        "The Witcher",
        "Thief",
        "Titanfall",
        "Tomb Raider",
        "Tom Clancy",
        "Total War",
        "Trine",
        "Tropico",
        "Uncharted",
        "Unreal",
        "Warhammer",
        "Wasteland",
        "Watch Dogs",
        "Wolfenstein",
        "Worms",
        "XCOM",
        "Yakuza",
    }
)

# Ghost name patterns to skip during franchise detection.
GHOST_PREFIXES: tuple[str, ...] = ("App ", "Unknown App ", "Unbekannte App ")
