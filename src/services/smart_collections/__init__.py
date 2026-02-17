"""Smart Collections service: rule-based dynamic game collections.

Provides models, evaluation engine, and manager for creating and maintaining
Smart Collections that automatically match games based on configurable rules.
"""

from __future__ import annotations

from src.services.smart_collections.evaluator import SmartCollectionEvaluator
from src.services.smart_collections.models import (
    FilterField,
    LogicOperator,
    Operator,
    SmartCollection,
    SmartCollectionRule,
    SmartCollectionRuleGroup,
)
from src.services.smart_collections.smart_collection_manager import SmartCollectionManager

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
