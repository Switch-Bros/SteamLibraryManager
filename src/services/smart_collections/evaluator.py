# src/services/smart_collections/evaluator.py

"""Smart Collection rule evaluation engine.

Evaluates SmartCollectionRule instances against Game objects, supporting
text matching (equals, contains, starts_with, ends_with, regex),
numeric comparison (>, <, >=, <=, between), and boolean checks.
"""

from __future__ import annotations

import logging
import re
from typing import TYPE_CHECKING

from src.services.smart_collections.models import (
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
    from src.core.game import Game

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
        """Checks if a game matches a Smart Collection's rules.

        When the collection has groups, evaluates using grouped logic
        (each group has its own internal AND/OR, and the top-level logic
        combines group results).  Otherwise falls back to the legacy flat
        rule evaluation.

        Args:
            game: The game to evaluate.
            collection: The Smart Collection with rules.

        Returns:
            True if the game matches the collection's rules.
        """
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
        """Evaluates a game against grouped rules.

        Each group is evaluated independently with its internal logic operator,
        then group results are combined with the collection's top-level logic.

        Args:
            game: The game to evaluate.
            collection: The Smart Collection with groups.

        Returns:
            True if the game matches according to the group logic.
        """
        group_results = [self._evaluate_group(game, g) for g in collection.groups]
        if collection.logic == LogicOperator.AND:
            return all(group_results)
        return any(group_results)

    def _evaluate_group(self, game: Game, group: SmartCollectionRuleGroup) -> bool:
        """Evaluates a single rule group against a game.

        Args:
            game: The game to evaluate.
            group: The rule group with its internal logic operator.

        Returns:
            True if the game matches the group's rules. False if the group has no rules.
        """
        if not group.rules:
            return False

        if group.logic == LogicOperator.AND:
            return all(self._evaluate_rule(game, rule) for rule in group.rules)
        return any(self._evaluate_rule(game, rule) for rule in group.rules)

    def _evaluate_rule(self, game: Game, rule: SmartCollectionRule) -> bool:
        """Evaluates a single rule against a game, handling negation.

        Args:
            game: The game to check.
            rule: The rule to evaluate.

        Returns:
            True if the game matches the rule (or fails it when negated).
        """
        result = self._match_rule(game, rule)
        return not result if rule.negated else result

    def _match_rule(self, game: Game, rule: SmartCollectionRule) -> bool:
        """Matches a single rule against a game (without negation).

        Args:
            game: The game to check.
            rule: The rule to evaluate.

        Returns:
            True if the game's field value matches the rule's operator and value.
        """
        field_value = self._get_field_value(game, rule.field)

        if rule.field in _TEXT_LIST_FIELDS:
            if not isinstance(field_value, list):
                field_value = [str(field_value)] if field_value else []
            return self._match_text_list(field_value, rule.operator, rule.value)

        if rule.field in _TEXT_SINGLE_FIELDS or rule.field in _ENUM_FIELDS:
            return self._match_text_single(str(field_value), rule.operator, rule.value)

        if rule.field in _NUMERIC_FIELDS:
            num_val: str | float | int = field_value if isinstance(field_value, (int, float)) else str(field_value)
            return self._match_numeric(num_val, rule.operator, rule.value, rule.value_max)

        if rule.field in _BOOL_FIELDS:
            return self._match_boolean(bool(field_value), rule.operator)

        logger.warning("Unknown field category for %s", rule.field)
        return False

    def _get_field_value(self, game: Game, fld: FilterField) -> str | list[str] | float | bool:
        """Extracts the field value from a Game object.

        Args:
            game: The game to get the value from.
            fld: The filter field to extract.

        Returns:
            The field value (type depends on the field category).
        """
        attr_name = field_to_game_attr(fld)

        # playtime_hours is a property, not a stored field
        if fld == FilterField.PLAYTIME_HOURS:
            return game.playtime_hours

        return getattr(game, attr_name, "")

    def _match_text_list(self, values: list[str], operator: Operator, target: str) -> bool:
        """Matches an operator against a list of text values (tags, genres, etc.).

        For list fields, the rule matches if ANY item in the list satisfies the operator.

        Args:
            values: The list of string values from the game.
            operator: The comparison operator.
            target: The target value to compare against.

        Returns:
            True if any item in the list matches the operator and target.
        """
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
        """Matches an operator against a single text value.

        Args:
            value: The string value from the game.
            operator: The comparison operator.
            target: The target value to compare against.

        Returns:
            True if the value matches the operator and target.
        """
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
        """Matches a numeric operator against a value.

        Args:
            value: The numeric value from the game (may be string).
            operator: The comparison operator.
            target: The target value (as string, will be parsed).
            target_max: The upper bound for BETWEEN operator.

        Returns:
            True if the numeric comparison succeeds.
        """
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
            return num_target <= num_value <= num_max

        return False

    def _match_boolean(self, value: bool, operator: Operator) -> bool:
        """Matches a boolean operator.

        Args:
            value: The boolean value from the game.
            operator: IS_TRUE or IS_FALSE.

        Returns:
            True if the boolean check matches.
        """
        if operator == Operator.IS_TRUE:
            return value is True
        if operator == Operator.IS_FALSE:
            return value is False
        return False

    def evaluate_batch(self, games: list[Game], collection: SmartCollection) -> list[Game]:
        """Returns all games matching the collection rules.

        Args:
            games: List of games to evaluate.
            collection: The Smart Collection with rules.

        Returns:
            List of games that match the collection's rules.
        """
        return [game for game in games if self.evaluate(game, collection)]
