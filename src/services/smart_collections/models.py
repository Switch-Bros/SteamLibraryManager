# src/services/smart_collections/models.py

"""Data models for Smart Collections: enums, dataclasses, and serialization helpers.

Defines the rule language for Smart Collections including filter fields,
operators, logic operators, and the SmartCollection/SmartCollectionRule
dataclasses. Also provides serialization helpers for JSON persistence.
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field
from enum import Enum

__all__ = [
    "FIELD_CATEGORIES",
    "FilterField",
    "LogicOperator",
    "Operator",
    "SmartCollection",
    "SmartCollectionRule",
    "VALID_OPERATORS",
    "collection_from_json",
    "collection_to_json",
    "field_to_game_attr",
    "rule_from_dict",
    "rule_to_dict",
]

logger = logging.getLogger("steamlibmgr.smart_collections.models")


class FilterField(Enum):
    """Available fields for Smart Collection rules."""

    # Text list fields (game has list of values)
    TAG = "tag"
    GENRE = "genre"
    PLATFORM = "platform"
    LANGUAGE = "language"
    CATEGORY = "category"

    # Text single fields
    NAME = "name"
    DEVELOPER = "developer"
    PUBLISHER = "publisher"
    APP_TYPE = "app_type"

    # Numeric fields
    PLAYTIME_HOURS = "playtime_hours"
    RELEASE_YEAR = "release_year"
    REVIEW_SCORE = "review_score"
    REVIEW_COUNT = "review_count"
    HLTB_MAIN = "hltb_main"
    ACHIEVEMENT_PCT = "achievement_pct"
    ACHIEVEMENT_TOTAL = "achievement_total"

    # Enum/Choice fields
    STEAM_DECK = "steam_deck"
    PROTONDB = "protondb"

    # Boolean fields
    INSTALLED = "installed"
    HIDDEN = "hidden"
    ACHIEVEMENT_PERFECT = "achievement_perfect"


class Operator(Enum):
    """Comparison operators for Smart Collection rules."""

    # Text operators
    EQUALS = "equals"
    CONTAINS = "contains"
    STARTS_WITH = "starts_with"
    ENDS_WITH = "ends_with"
    REGEX = "regex"

    # Numeric operators
    GREATER_THAN = "greater_than"
    LESS_THAN = "less_than"
    GREATER_EQUAL = "greater_equal"
    LESS_EQUAL = "less_equal"
    BETWEEN = "between"

    # Boolean operators
    IS_TRUE = "is_true"
    IS_FALSE = "is_false"


class LogicOperator(Enum):
    """Top-level logic operator between rules."""

    AND = "AND"
    OR = "OR"


# Text operators shared by text-list and text-single fields
_TEXT_OPS: list[Operator] = [
    Operator.EQUALS,
    Operator.CONTAINS,
    Operator.STARTS_WITH,
    Operator.ENDS_WITH,
    Operator.REGEX,
]

# Numeric operators shared by all numeric fields
_NUMERIC_OPS: list[Operator] = [
    Operator.EQUALS,
    Operator.GREATER_THAN,
    Operator.LESS_THAN,
    Operator.GREATER_EQUAL,
    Operator.LESS_EQUAL,
    Operator.BETWEEN,
]

# Boolean operators
_BOOL_OPS: list[Operator] = [
    Operator.IS_TRUE,
    Operator.IS_FALSE,
]

VALID_OPERATORS: dict[FilterField, list[Operator]] = {
    # Text list fields
    FilterField.TAG: _TEXT_OPS,
    FilterField.GENRE: _TEXT_OPS,
    FilterField.PLATFORM: _TEXT_OPS,
    FilterField.LANGUAGE: _TEXT_OPS,
    FilterField.CATEGORY: _TEXT_OPS,
    # Text single fields
    FilterField.NAME: _TEXT_OPS,
    FilterField.DEVELOPER: _TEXT_OPS,
    FilterField.PUBLISHER: _TEXT_OPS,
    FilterField.APP_TYPE: _TEXT_OPS,
    # Enum/Choice fields (treated as text single)
    FilterField.STEAM_DECK: _TEXT_OPS,
    FilterField.PROTONDB: _TEXT_OPS,
    # Numeric fields
    FilterField.PLAYTIME_HOURS: _NUMERIC_OPS,
    FilterField.RELEASE_YEAR: _NUMERIC_OPS,
    FilterField.REVIEW_SCORE: _NUMERIC_OPS,
    FilterField.REVIEW_COUNT: _NUMERIC_OPS,
    FilterField.HLTB_MAIN: _NUMERIC_OPS,
    FilterField.ACHIEVEMENT_PCT: _NUMERIC_OPS,
    FilterField.ACHIEVEMENT_TOTAL: _NUMERIC_OPS,
    # Boolean fields
    FilterField.INSTALLED: _BOOL_OPS,
    FilterField.HIDDEN: _BOOL_OPS,
    FilterField.ACHIEVEMENT_PERFECT: _BOOL_OPS,
}

FIELD_CATEGORIES: dict[str, list[FilterField]] = {
    "text_list": [
        FilterField.TAG,
        FilterField.GENRE,
        FilterField.PLATFORM,
        FilterField.LANGUAGE,
        FilterField.CATEGORY,
    ],
    "text_single": [
        FilterField.NAME,
        FilterField.DEVELOPER,
        FilterField.PUBLISHER,
        FilterField.APP_TYPE,
    ],
    "numeric": [
        FilterField.PLAYTIME_HOURS,
        FilterField.RELEASE_YEAR,
        FilterField.REVIEW_SCORE,
        FilterField.REVIEW_COUNT,
        FilterField.HLTB_MAIN,
        FilterField.ACHIEVEMENT_PCT,
        FilterField.ACHIEVEMENT_TOTAL,
    ],
    "enum": [
        FilterField.STEAM_DECK,
        FilterField.PROTONDB,
    ],
    "boolean": [
        FilterField.INSTALLED,
        FilterField.HIDDEN,
        FilterField.ACHIEVEMENT_PERFECT,
    ],
}

# Maps FilterField to the Game dataclass attribute name
_FIELD_TO_ATTR: dict[FilterField, str] = {
    FilterField.TAG: "tags",
    FilterField.GENRE: "genres",
    FilterField.PLATFORM: "platforms",
    FilterField.LANGUAGE: "languages",
    FilterField.CATEGORY: "categories",
    FilterField.NAME: "name",
    FilterField.DEVELOPER: "developer",
    FilterField.PUBLISHER: "publisher",
    FilterField.APP_TYPE: "app_type",
    FilterField.PLAYTIME_HOURS: "playtime_hours",
    FilterField.RELEASE_YEAR: "release_year",
    FilterField.REVIEW_SCORE: "review_percentage",
    FilterField.REVIEW_COUNT: "review_count",
    FilterField.HLTB_MAIN: "hltb_main_story",
    FilterField.ACHIEVEMENT_PCT: "achievement_percentage",
    FilterField.ACHIEVEMENT_TOTAL: "achievement_total",
    FilterField.STEAM_DECK: "steam_deck_status",
    FilterField.PROTONDB: "proton_db_rating",
    FilterField.INSTALLED: "installed",
    FilterField.HIDDEN: "hidden",
    FilterField.ACHIEVEMENT_PERFECT: "achievement_perfect",
}


def field_to_game_attr(fld: FilterField) -> str:
    """Maps a FilterField to the corresponding Game dataclass attribute name.

    Args:
        fld: The filter field to map.

    Returns:
        The attribute name on the Game dataclass.
    """
    return _FIELD_TO_ATTR[fld]


@dataclass(frozen=True)
class SmartCollectionRule:
    """A single rule in a Smart Collection.

    Attributes:
        field: Which game field to match against.
        operator: The comparison operator.
        value: The target value for comparison.
        value_max: Second value for BETWEEN operator.
        negated: If True, the rule result is inverted (NOT).
    """

    field: FilterField
    operator: Operator
    value: str = ""
    value_max: str = ""
    negated: bool = False


@dataclass
class SmartCollection:
    """A Smart Collection with its rules and metadata.

    Attributes:
        collection_id: Database primary key (0 for unsaved).
        name: Display name of the collection.
        description: Optional description.
        icon: Emoji icon for display.
        logic: Top-level logic operator between rules (AND/OR).
        rules: List of filter rules.
        is_active: Whether the collection is evaluated on refresh.
        auto_sync: Whether to sync matching games to Steam cloud.
        last_evaluated: Unix timestamp of last evaluation.
        created_at: Unix timestamp of creation.
    """

    collection_id: int = 0
    name: str = ""
    description: str = ""
    icon: str = "\U0001f9e0"
    logic: LogicOperator = LogicOperator.OR
    rules: list[SmartCollectionRule] = field(default_factory=list)
    is_active: bool = True
    auto_sync: bool = True
    last_evaluated: int = 0
    created_at: int = 0


# ========================================================================
# SERIALIZATION HELPERS
# ========================================================================


def rule_to_dict(rule: SmartCollectionRule) -> dict:
    """Serializes a SmartCollectionRule to a JSON-compatible dict.

    Args:
        rule: The rule to serialize.

    Returns:
        Dict with field, operator, value, value_max, negated.
    """
    return {
        "field": rule.field.value,
        "operator": rule.operator.value,
        "value": rule.value,
        "value_max": rule.value_max,
        "negated": rule.negated,
    }


def rule_from_dict(data: dict) -> SmartCollectionRule:
    """Deserializes a SmartCollectionRule from a dict.

    Args:
        data: Dict with field, operator, value, value_max, negated.

    Returns:
        A SmartCollectionRule instance.

    Raises:
        ValueError: If field or operator values are invalid.
    """
    return SmartCollectionRule(
        field=FilterField(data["field"]),
        operator=Operator(data["operator"]),
        value=data.get("value", ""),
        value_max=data.get("value_max", ""),
        negated=data.get("negated", False),
    )


def collection_to_json(collection: SmartCollection) -> str:
    """Serializes a SmartCollection's rules to a JSON string for DB storage.

    Args:
        collection: The SmartCollection to serialize.

    Returns:
        JSON string with logic and rules array.
    """
    payload = {
        "logic": collection.logic.value,
        "rules": [rule_to_dict(r) for r in collection.rules],
    }
    return json.dumps(payload, ensure_ascii=False)


def collection_from_json(rules_json: str, collection: SmartCollection | None = None) -> SmartCollection:
    """Deserializes rules JSON into a SmartCollection (or updates an existing one).

    Args:
        rules_json: JSON string with logic and rules array.
        collection: Optional existing SmartCollection to update. If None, a new one is created.

    Returns:
        SmartCollection with deserialized rules and logic.
    """
    if collection is None:
        collection = SmartCollection()

    if not rules_json:
        return collection

    try:
        data = json.loads(rules_json)
    except json.JSONDecodeError:
        logger.warning("Invalid rules JSON: %s", rules_json[:100])
        return collection

    if "logic" in data:
        try:
            collection.logic = LogicOperator(data["logic"])
        except ValueError:
            logger.warning("Unknown logic operator: %s", data["logic"])

    if "rules" in data:
        parsed_rules: list[SmartCollectionRule] = []
        for rule_data in data["rules"]:
            try:
                parsed_rules.append(rule_from_dict(rule_data))
            except (ValueError, KeyError) as exc:
                logger.warning("Skipping invalid rule %s: %s", rule_data, exc)
        collection.rules = parsed_rules

    collection.last_evaluated = data.get("last_evaluated", collection.last_evaluated)
    return collection


def now_ts() -> int:
    """Returns the current Unix timestamp as integer.

    Returns:
        Current time as integer seconds since epoch.
    """
    return int(time.time())
