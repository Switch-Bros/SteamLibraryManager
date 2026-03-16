#
# steam_library_manager/services/smart_collections/evaluator.py
# Evaluates smart collection rules against game records
#
# Copyright © 2025-2026 SwitchBros
# Licensed under the MIT License. See LICENSE for details.
#

#
# steam_library_manager/services/smart_collections/evaluator.py
# Smart Collection rule evaluation engine.
#
# Copyright © 2025-2026 SwitchBros
# Licensed under the MIT License. See LICENSE for details.
#

from __future__ import annotations

import logging
import re
from typing import TYPE_CHECKING

from steam_library_manager.services.smart_collections.models import (
    FIELD_CATEGORIES,
    FilterField,
    LogicOperator,
    Operator,
    SmartCollection,
    SmartCollectionRule,
    SmartCollectionRuleGroup,
    field_to_game_attr,
)

if TYPE_CHECKING:
    from steam_library_manager.core.game import Game

__all__ = ["SmartCollectionEvaluator"]

logger = logging.getLogger("steamlibmgr.smart_collections.evaluator")

# Pre-compute field category sets for fast lookup
_TEXT_LIST_FIELDS: frozenset[FilterField] = frozenset(FIELD_CATEGORIES["text_list"])
_TEXT_SINGLE_FIELDS: frozenset[FilterField] = frozenset(FIELD_CATEGORIES["text_single"])
_NUMERIC_FIELDS: frozenset[FilterField] = frozenset(FIELD_CATEGORIES["numeric"])
_ENUM_FIELDS: frozenset[FilterField] = frozenset(FIELD_CATEGORIES["enum"])
_BOOL_FIELDS: frozenset[FilterField] = frozenset(FIELD_CATEGORIES["boolean"])


class SmartCollectionEvaluator:
    """Evaluates Smart Collection rules against Game objects."""

    def evaluate(self, game: Game, collection: SmartCollection) -> bool:
        """Checks if a game matches a Smart Collection's rules."""
        if collection.groups:
            return self._evaluate_groups(game, collection)

        # Legacy flat-rule path
        if not collection.rules:
            return False

        if collection.logic == LogicOperator.AND:
            return all(self._evaluate_rule(game, rule) for rule in collection.rules)
        # OR
        return any(self._evaluate_rule(game, rule) for rule in collection.rules)

    def _evaluate_groups(self, game: Game, collection: SmartCollection) -> bool:
        """Evaluates a game against grouped rules."""
        group_results = [self._evaluate_group(game, g) for g in collection.groups]
        if collection.logic == LogicOperator.AND:
            return all(group_results)
        return any(group_results)

    def _evaluate_group(self, game: Game, group: SmartCollectionRuleGroup) -> bool:
        """Evaluates a single rule group against a game."""
        if not group.rules:
            return False

        if group.logic == LogicOperator.AND:
            return all(self._evaluate_rule(game, rule) for rule in group.rules)
        return any(self._evaluate_rule(game, rule) for rule in group.rules)

    def _evaluate_rule(self, game: Game, rule: SmartCollectionRule) -> bool:
        """Evaluates a single rule against a game, handling negation."""
        result = self._match_rule(game, rule)
        return not result if rule.negated else result

    def _match_rule(self, game: Game, rule: SmartCollectionRule) -> bool:
        """Matches a single rule against a game (without negation)."""
        # Fast path: TAG + EQUALS with tag_id -> language-independent ID comparison
        if rule.field == FilterField.TAG and rule.operator == Operator.EQUALS and rule.tag_id is not None:
            game_tag_ids = getattr(game, "tag_ids", None)
            if game_tag_ids:
                return rule.tag_id in game_tag_ids
            # Fallback to string comparison if game has no tag_ids

        field_value = self._get_field_value(game, rule.field)

        if rule.field in _TEXT_LIST_FIELDS:
            if not isinstance(field_value, (list, tuple)):
                field_value = [str(field_value)] if field_value else []
            else:
                field_value = list(field_value)
            return self._match_text_list(field_value, rule.operator, rule.value)

        if rule.field in _TEXT_SINGLE_FIELDS or rule.field in _ENUM_FIELDS:
            return self._match_text_single(str(field_value), rule.operator, rule.value)

        if rule.field in _NUMERIC_FIELDS:
            # RELEASE_YEAR stores UNIX timestamp but user compares by year
            if rule.field == FilterField.RELEASE_YEAR and isinstance(field_value, int) and field_value > 9999:
                from steam_library_manager.utils.date_utils import year_from_timestamp

                yr = year_from_timestamp(field_value)
                num_val: str | float | int = float(yr) if yr else 0
            else:
                num_val = field_value if isinstance(field_value, (int, float)) else str(field_value)
            return self._match_numeric(num_val, rule.operator, rule.value, rule.value_max)

        if rule.field in _BOOL_FIELDS:
            return self._match_boolean(bool(field_value), rule.operator)

        logger.warning("Unknown field category for %s", rule.field)
        return False

    def _get_field_value(self, game: Game, fld: FilterField) -> str | list[str] | float | bool:
        """Extracts the field value from a Game object."""
        attr_name = field_to_game_attr(fld)

        # playtime_hours is a property, not a stored field
        if fld == FilterField.PLAYTIME_HOURS:
            return game.playtime_hours

        return getattr(game, attr_name, "")

    def _match_text_list(self, values: list[str], operator: Operator, target: str) -> bool:
        """Matches an operator against a list of text values (tags, genres, etc.)."""
        if not values:
            return False

        target_lower = target.lower()

        for val in values:
            val_lower = val.lower()

            if operator == Operator.EQUALS and val_lower == target_lower:
                return True
            if operator == Operator.CONTAINS and target_lower in val_lower:
                return True
            if operator == Operator.STARTS_WITH and val_lower.startswith(target_lower):
                return True
            if operator == Operator.ENDS_WITH and val_lower.endswith(target_lower):
                return True
            if operator == Operator.REGEX:
                try:
                    if re.search(target, val, re.IGNORECASE):
                        return True
                except re.error:
                    return False

        return False

    def _match_text_single(self, value: str, operator: Operator, target: str) -> bool:
        """Matches an operator against a single text value."""
        value_lower = value.lower()
        target_lower = target.lower()

        if operator == Operator.EQUALS:
            return value_lower == target_lower
        if operator == Operator.CONTAINS:
            return target_lower in value_lower
        if operator == Operator.STARTS_WITH:
            return value_lower.startswith(target_lower)
        if operator == Operator.ENDS_WITH:
            return value_lower.endswith(target_lower)
        if operator == Operator.REGEX:
            try:
                return bool(re.search(target, value, re.IGNORECASE))
            except re.error:
                return False

        return False

    def _match_numeric(self, value: str | float | int, operator: Operator, target: str, target_max: str) -> bool:
        """Matches a numeric operator against a value."""
        try:
            num_value = float(value) if not isinstance(value, (int, float)) else float(value)
        except (ValueError, TypeError):
            return False

        try:
            num_target = float(target) if target else 0.0
        except (ValueError, TypeError):
            return False

        if operator == Operator.EQUALS:
            return num_value == num_target
        if operator == Operator.GREATER_THAN:
            return num_value > num_target
        if operator == Operator.LESS_THAN:
            return num_value < num_target
        if operator == Operator.GREATER_EQUAL:
            return num_value >= num_target
        if operator == Operator.LESS_EQUAL:
            return num_value <= num_target
        if operator == Operator.BETWEEN:
            try:
                num_max = float(target_max) if target_max else 0.0
            except (ValueError, TypeError):
                return False
            lo, hi = min(num_target, num_max), max(num_target, num_max)
            return lo <= num_value <= hi

        return False

    def _match_boolean(self, value: bool, operator: Operator) -> bool:
        """Matches a boolean operator."""
        if operator == Operator.IS_TRUE:
            return value is True
        if operator == Operator.IS_FALSE:
            return value is False
        return False

    def evaluate_batch(self, games: list[Game], collection: SmartCollection) -> list[Game]:
        """Returns all games matching the collection rules."""
        return [game for game in games if self.evaluate(game, collection)]
