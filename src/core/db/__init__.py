"""Database module — split from monolithic database.py.

All mixins compose into the Database class via multiple inheritance.
The MRO (Method Resolution Order) ensures ConnectionBase.__init__
runs first, then SchemaMixin._ensure_schema() creates/migrates
the schema.
"""

from __future__ import annotations

from src.core.db.connection import ConnectionBase
from src.core.db.enrichment_queries import EnrichmentQueryMixin
from src.core.db.game_batch_queries import GameBatchQueryMixin
from src.core.db.game_queries import GameQueryMixin
from src.core.db.models import (
    DatabaseEntry,
    ImportStats,
    database_entry_to_game,
    is_placeholder_name,
)
from src.core.db.modification_queries import ModificationMixin
from src.core.db.schema import SchemaMixin
from src.core.db.smart_collection_queries import SmartCollectionMixin
from src.core.db.tag_queries import TagQueryMixin

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
    ConnectionBase,
):
    """Main database class composing all query mixins.

    Inherits connection management from ConnectionBase,
    schema handling from SchemaMixin, and all query methods
    from the remaining mixins.
    """

    pass
