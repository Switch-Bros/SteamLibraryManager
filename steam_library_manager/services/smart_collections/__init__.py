#
# steam_library_manager/services/smart_collections/__init__.py
# Smart collections package
#
# Copyright © 2025-2026 SwitchBros
# Licensed under the MIT License. See LICENSE for details.
#
from __future__ import annotations

from steam_library_manager.services.smart_collections.evaluator import SmartCollectionEvaluator
from steam_library_manager.services.smart_collections.models import (
    FilterField,
    LogicOperator,
    Operator,
    SmartCollection,
    SmartCollectionRule,
    SmartCollectionRuleGroup,
)
from steam_library_manager.services.smart_collections.smart_collection_manager import SmartCollectionManager

__all__: list[str] = [
    "FilterField",
    "LogicOperator",
    "Operator",
    "SmartCollection",
    "SmartCollectionEvaluator",
    "SmartCollectionManager",
    "SmartCollectionRule",
    "SmartCollectionRuleGroup",
]
