#
# steam_library_manager/core/db/__init__.py
# db package - composes Database class from connection and mixin modules
#
# Copyright © 2025-2026 SwitchBros
# Licensed under the MIT License. See LICENSE for details.
#

from __future__ import annotations

# connection + schema
from steam_library_manager.core.db.connection import ConnectionBase
from steam_library_manager.core.db.schema import SchemaMixin

# query mixins
from steam_library_manager.core.db.curator_mixin import CuratorMixin
from steam_library_manager.core.db.enrichment_queries import EnrichmentQueryMixin
from steam_library_manager.core.db.game_batch_queries import GameBatchQueryMixin
from steam_library_manager.core.db.game_queries import GameQueryMixin
from steam_library_manager.core.db.modification_queries import ModificationMixin
from steam_library_manager.core.db.smart_collection_queries import SmartCollectionMixin
from steam_library_manager.core.db.tag_queries import TagQueryMixin

# data models
from steam_library_manager.core.db.models import (
    DatabaseEntry,
    ImportStats,
    database_entry_to_game,
    is_placeholder_name,
)

__all__ = [
    "Database",
    "DatabaseEntry",
    "ImportStats",
    "database_entry_to_game",
    "is_placeholder_name",
]


class Database(
    SchemaMixin,
    GameQueryMixin,
    GameBatchQueryMixin,
    EnrichmentQueryMixin,
    SmartCollectionMixin,
    TagQueryMixin,
    ModificationMixin,
    CuratorMixin,
    ConnectionBase,
):
    """Composes all query mixins on top of ConnectionBase."""

    pass
