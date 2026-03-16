#
# steam_library_manager/services/smart_collections/templates.py
# Predefined Smart Collection templates for quick-start creation
#
# Copyright © 2025-2026 SwitchBros
# Licensed under the MIT License. See LICENSE for details.
#

from __future__ import annotations

from dataclasses import dataclass

from steam_library_manager.services.smart_collections.models import (
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
    """A predefined Smart Collection template."""

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
    """Shorthand factory for creating a SmartCollectionRule."""
    return SmartCollectionRule(
        field=fld,
        operator=op,
        value=value,
        value_max=value_max,
        negated=negated,
    )


def _group(logic: LogicOperator, *rules: SmartCollectionRule) -> SmartCollectionRuleGroup:
    """Shorthand factory for creating a SmartCollectionRuleGroup."""
    return SmartCollectionRuleGroup(logic=logic, rules=rules)


# Template definitions

_TEMPLATES: list[SmartCollectionTemplate] = [
    # Quality
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
    # Completion
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
    # Time
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
    # Platform
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
    # Examples
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
    """Returns all available templates as a flat list."""
    return list(_TEMPLATES)


def get_template_by_key(key: str) -> SmartCollectionTemplate | None:
    """Looks up a template by its unique key."""
    for tmpl in _TEMPLATES:
        if tmpl.key == key:
            return tmpl
    return None
