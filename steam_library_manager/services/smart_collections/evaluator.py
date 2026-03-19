#
# steam_library_manager/services/smart_collections/evaluator.py
# Evaluates smart collection rules against game records
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

# pre-compute field category sets for fast lookup
_TXT_LIST = frozenset(FIELD_CATEGORIES["text_list"])
_TXT_SINGLE = frozenset(FIELD_CATEGORIES["text_single"])
_NUM = frozenset(FIELD_CATEGORIES["numeric"])
_ENUM = frozenset(FIELD_CATEGORIES["enum"])
_BOOL = frozenset(FIELD_CATEGORIES["boolean"])


class SmartCollectionEvaluator:
    """Evaluates Smart Collection rules against Game objects."""

    def evaluate(self, g: Game, col: SmartCollection):
        # check whether game satisfies collection's filter criteria
        if col.groups:
            return self._eval_grps(g, col)

        # legacy flat-rule path
        if not col.rules:
            return False

        if col.logic == LogicOperator.AND:
            return all(self._eval_rule(g, r) for r in col.rules)
        # OR
        return any(self._eval_rule(g, r) for r in col.rules)

    def _eval_grps(self, g, col):
        res = [self._eval_grp(g, grp) for grp in col.groups]
        if col.logic == LogicOperator.AND:
            return all(res)
        return any(res)

    def _eval_grp(self, g, grp: SmartCollectionRuleGroup):
        if not grp.rules:
            return False

        chk = all if grp.logic == LogicOperator.AND else any
        return chk(self._eval_rule(g, r) for r in grp.rules)

    def _eval_rule(self, g, r: SmartCollectionRule):
        # apply negation wrapper around match
        m = self._match(g, r)
        return not m if r.negated else m

    def _match(self, g, r: SmartCollectionRule):
        # core rule matching (without negation)
        # fast path: TAG + EQUALS with tag_id
        if r.field == FilterField.TAG and r.operator == Operator.EQUALS and r.tag_id is not None:
            ids = getattr(g, "tag_ids", None)
            if ids:
                return r.tag_id in ids

        raw = self._get_val(g, r.field)

        if r.field in _TXT_LIST:
            if not isinstance(raw, (list, tuple)):
                items = [str(raw)] if raw else []
            else:
                items = list(raw)
            return self._match_txt_list(items, r.operator, r.value)

        if r.field in _TXT_SINGLE or r.field in _ENUM:
            return self._match_txt(str(raw), r.operator, r.value)

        if r.field in _NUM:
            # RELEASE_YEAR stores UNIX timestamp but user compares by year
            if r.field == FilterField.RELEASE_YEAR and isinstance(raw, int) and raw > 9999:
                from steam_library_manager.utils.date_utils import year_from_timestamp

                yr = year_from_timestamp(raw)
                num_val = float(yr) if yr else 0
            else:
                num_val = raw if isinstance(raw, (int, float)) else str(raw)
            return self._match_num(num_val, r.operator, r.value, r.value_max)

        if r.field in _BOOL:
            return self._match_bool(bool(raw), r.operator)

        logger.warning("Unknown field category for %s" % r.field)
        return False

    def _get_val(self, g, fld):
        attr = field_to_game_attr(fld)

        # playtime_hours is computed, not stored
        if fld == FilterField.PLAYTIME_HOURS:
            return g.playtime_hours

        return getattr(g, attr, "")

    def _match_txt_list(self, vals, op, tgt):
        if not vals:
            return False

        t = tgt.lower()

        for v in vals:
            low = v.lower()

            if op == Operator.EQUALS and low == t:
                return True
            if op == Operator.CONTAINS and t in low:
                return True
            if op == Operator.STARTS_WITH and low.startswith(t):
                return True
            if op == Operator.ENDS_WITH and low.endswith(t):
                return True
            if op == Operator.REGEX:
                try:
                    if re.search(tgt, v, re.IGNORECASE):
                        return True
                except re.error:
                    return False

        return False

    def _match_txt(self, val, op, tgt):
        low_val = val.lower()
        low_tgt = tgt.lower()

        if op == Operator.EQUALS:
            return low_val == low_tgt
        if op == Operator.CONTAINS:
            return low_tgt in low_val
        if op == Operator.STARTS_WITH:
            return low_val.startswith(low_tgt)
        if op == Operator.ENDS_WITH:
            return low_val.endswith(low_tgt)
        if op == Operator.REGEX:
            try:
                return bool(re.search(tgt, val, re.IGNORECASE))
            except re.error:
                return False

        return False

    def _match_num(self, val, op, tgt, tgt_max):
        try:
            n = float(val)
        except (ValueError, TypeError):
            return False

        try:
            t = float(tgt) if tgt else 0.0
        except (ValueError, TypeError):
            return False

        if op == Operator.EQUALS:
            return n == t
        if op == Operator.GREATER_THAN:
            return n > t
        if op == Operator.LESS_THAN:
            return n < t
        if op == Operator.GREATER_EQUAL:
            return n >= t
        if op == Operator.LESS_EQUAL:
            return n <= t

        if op == Operator.BETWEEN:
            try:
                upper = float(tgt_max) if tgt_max else 0.0
            except (ValueError, TypeError):
                return False
            lo, hi = min(t, upper), max(t, upper)
            return lo <= n <= hi

        return False

    def _match_bool(self, val, op):
        if op == Operator.IS_TRUE:
            return val is True
        if op == Operator.IS_FALSE:
            return val is False
        return False

    def evaluate_batch(self, games: list[Game], col: SmartCollection) -> list[Game]:
        # filter game list down to those matching collection
        return [g for g in games if self.evaluate(g, col)]
