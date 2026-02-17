# src/services/smart_collections/templates.py

"""Predefined Smart Collection templates for quick-start creation.

Provides a set of built-in templates organized by category (Quality, Completion,
Time, Platform, Examples) that users can apply as starting points for new
Smart Collections.
"""

from __future__ import annotations

from dataclasses import dataclass

from src.services.smart_collections.models import (
    FilterField,
    LogicOperator,
    Operator,
    SmartCollection,
    SmartCollectionRule,
    SmartCollectionRuleGroup,
)

__all__ = [
    "TEMPLATE_CATEGORIES",
    "SmartCollectionTemplate",
    "get_all_templates",
    "get_template_by_key",
]


@dataclass(frozen=True)
class SmartCollectionTemplate:
    """A predefined Smart Collection template.

    Attributes:
        key: Unique template identifier, used as i18n lookup suffix.
        category: Category key for UI grouping (e.g. 'quality', 'completion').
        collection: The pre-configured SmartCollection to use as a starting point.
    """

    key: str
    category: str
    collection: SmartCollection


def _rule(
    fld: FilterField,
    op: Operator,
    value: str = "",
    value_max: str = "",
    *,
    negated: bool = False,
) -> SmartCollectionRule:
    """Shorthand factory for creating a SmartCollectionRule.

    Args:
        fld: The filter field.
        op: The comparison operator.
        value: The comparison value.
        value_max: The upper bound for BETWEEN operator.
        negated: Whether to negate the result.

    Returns:
        A frozen SmartCollectionRule instance.
    """
    return SmartCollectionRule(
        field=fld,
        operator=op,
        value=value,
        value_max=value_max,
        negated=negated,
    )


def _group(logic: LogicOperator, *rules: SmartCollectionRule) -> SmartCollectionRuleGroup:
    """Shorthand factory for creating a SmartCollectionRuleGroup.

    Args:
        logic: The logic operator within this group.
        rules: The rules in this group.

    Returns:
        A frozen SmartCollectionRuleGroup instance.
    """
    return SmartCollectionRuleGroup(logic=logic, rules=rules)


# ========================================================================
# TEMPLATE DEFINITIONS
# ========================================================================

_TEMPLATES: list[SmartCollectionTemplate] = [
    # --- Quality ---
    SmartCollectionTemplate(
        key="highly_rated",
        category="quality",
        collection=SmartCollection(
            name="",  # Filled from i18n at runtime
            description="",
            logic=LogicOperator.AND,
            groups=[
                _group(
                    LogicOperator.AND,
                    _rule(FilterField.REVIEW_SCORE, Operator.GREATER_EQUAL, "90"),
                ),
            ],
        ),
    ),
    SmartCollectionTemplate(
        key="mixed_negative",
        category="quality",
        collection=SmartCollection(
            name="",
            description="",
            logic=LogicOperator.AND,
            groups=[
                _group(
                    LogicOperator.AND,
                    _rule(FilterField.REVIEW_SCORE, Operator.LESS_THAN, "50"),
                ),
            ],
        ),
    ),
    # --- Completion ---
    SmartCollectionTemplate(
        key="unplayed",
        category="completion",
        collection=SmartCollection(
            name="",
            description="",
            logic=LogicOperator.AND,
            groups=[
                _group(
                    LogicOperator.AND,
                    _rule(FilterField.PLAYTIME_HOURS, Operator.EQUALS, "0"),
                    _rule(FilterField.INSTALLED, Operator.IS_TRUE),
                ),
            ],
        ),
    ),
    SmartCollectionTemplate(
        key="perfect_games",
        category="completion",
        collection=SmartCollection(
            name="",
            description="",
            logic=LogicOperator.AND,
            groups=[
                _group(
                    LogicOperator.AND,
                    _rule(FilterField.ACHIEVEMENT_PERFECT, Operator.IS_TRUE),
                ),
            ],
        ),
    ),
    SmartCollectionTemplate(
        key="almost_done",
        category="completion",
        collection=SmartCollection(
            name="",
            description="",
            logic=LogicOperator.AND,
            groups=[
                _group(
                    LogicOperator.AND,
                    _rule(FilterField.ACHIEVEMENT_PCT, Operator.GREATER_EQUAL, "75"),
                    _rule(FilterField.ACHIEVEMENT_PERFECT, Operator.IS_FALSE),
                ),
            ],
        ),
    ),
    # --- Time ---
    SmartCollectionTemplate(
        key="quick_play",
        category="time",
        collection=SmartCollection(
            name="",
            description="",
            logic=LogicOperator.AND,
            groups=[
                _group(
                    LogicOperator.AND,
                    _rule(FilterField.HLTB_MAIN, Operator.LESS_THAN, "300"),
                ),
            ],
        ),
    ),
    SmartCollectionTemplate(
        key="long_games",
        category="time",
        collection=SmartCollection(
            name="",
            description="",
            logic=LogicOperator.AND,
            groups=[
                _group(
                    LogicOperator.AND,
                    _rule(FilterField.HLTB_MAIN, Operator.GREATER_EQUAL, "3000"),
                ),
            ],
        ),
    ),
    SmartCollectionTemplate(
        key="100h_club",
        category="time",
        collection=SmartCollection(
            name="",
            description="",
            logic=LogicOperator.AND,
            groups=[
                _group(
                    LogicOperator.AND,
                    _rule(FilterField.PLAYTIME_HOURS, Operator.GREATER_THAN, "100"),
                ),
            ],
        ),
    ),
    # --- Platform ---
    SmartCollectionTemplate(
        key="linux_native",
        category="platform",
        collection=SmartCollection(
            name="",
            description="",
            logic=LogicOperator.AND,
            groups=[
                _group(
                    LogicOperator.AND,
                    _rule(FilterField.PLATFORM, Operator.EQUALS, "linux"),
                ),
            ],
        ),
    ),
    SmartCollectionTemplate(
        key="deck_verified",
        category="platform",
        collection=SmartCollection(
            name="",
            description="",
            logic=LogicOperator.AND,
            groups=[
                _group(
                    LogicOperator.AND,
                    _rule(FilterField.STEAM_DECK, Operator.EQUALS, "verified"),
                ),
            ],
        ),
    ),
    # --- Examples ---
    SmartCollectionTemplate(
        key="hybrid_demo",
        category="examples",
        collection=SmartCollection(
            name="",
            description="",
            logic=LogicOperator.OR,
            groups=[
                _group(
                    LogicOperator.AND,
                    _rule(FilterField.TAG, Operator.CONTAINS, "LEGO"),
                    _rule(FilterField.PLATFORM, Operator.EQUALS, "linux"),
                ),
                _group(
                    LogicOperator.AND,
                    _rule(FilterField.GENRE, Operator.CONTAINS, "Action"),
                    _rule(FilterField.REVIEW_SCORE, Operator.GREATER_EQUAL, "80"),
                ),
            ],
        ),
    ),
    SmartCollectionTemplate(
        key="or_demo",
        category="examples",
        collection=SmartCollection(
            name="",
            description="",
            logic=LogicOperator.OR,
            groups=[
                _group(
                    LogicOperator.OR,
                    _rule(FilterField.TAG, Operator.CONTAINS, "LEGO"),
                    _rule(FilterField.TAG, Operator.CONTAINS, "Kampf"),
                ),
            ],
        ),
    ),
]

# Build category -> templates lookup
TEMPLATE_CATEGORIES: dict[str, list[SmartCollectionTemplate]] = {}
for _tmpl in _TEMPLATES:
    TEMPLATE_CATEGORIES.setdefault(_tmpl.category, []).append(_tmpl)


def get_all_templates() -> list[SmartCollectionTemplate]:
    """Returns all available templates as a flat list.

    Returns:
        List of all SmartCollectionTemplate instances.
    """
    return list(_TEMPLATES)


def get_template_by_key(key: str) -> SmartCollectionTemplate | None:
    """Looks up a template by its unique key.

    Args:
        key: The template key to search for.

    Returns:
        The matching template, or None if not found.
    """
    for tmpl in _TEMPLATES:
        if tmpl.key == key:
            return tmpl
    return None
