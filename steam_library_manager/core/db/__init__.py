"""Database module — split from monolithic database.py.

All mixins compose into the Database class via multiple inheritance.
The MRO (Method Resolution Order) ensures ConnectionBase.__init__
runs first, then SchemaMixin._ensure_schema() creates/migrates
the schema.
"""

from __future__ import annotations

from steam_library_manager.core.db.connection import ConnectionBase
from steam_library_manager.core.db.curator_mixin import CuratorMixin
from steam_library_manager.core.db.enrichment_queries import EnrichmentQueryMixin
from steam_library_manager.core.db.game_batch_queries import GameBatchQueryMixin
from steam_library_manager.core.db.game_queries import GameQueryMixin
from steam_library_manager.core.db.models import (
    DatabaseEntry,
    ImportStats,
    database_entry_to_game,
    is_placeholder_name,
)
from steam_library_manager.core.db.modification_queries import ModificationMixin
from steam_library_manager.core.db.schema import SchemaMixin
from steam_library_manager.core.db.smart_collection_queries import SmartCollectionMixin
from steam_library_manager.core.db.tag_queries import TagQueryMixin

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
    """Main database class composing all query mixins.

    Inherits connection management from ConnectionBase,
    schema handling from SchemaMixin, and all query methods
    from the remaining mixins.
    """

    pass
