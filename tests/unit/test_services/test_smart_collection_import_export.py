# tests/unit/test_services/test_smart_collection_import_export.py

"""Tests for Smart Collection export/import v1.1 (groups support)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.services.smart_collections.models import (
    FilterField,
    LogicOperator,
    Operator,
    SmartCollection,
    SmartCollectionRule,
    SmartCollectionRuleGroup,
)
from src.utils.smart_collection_exporter import SmartCollectionExporter
from src.utils.smart_collection_importer import SmartCollectionImporter

# ========================================================================
# FIXTURES
# ========================================================================


@pytest.fixture
def export_path(tmp_path: Path) -> Path:
    """Returns a temporary file path for export."""
    return tmp_path / "smart_collections_v11.json"


@pytest.fixture
def collection_with_groups() -> SmartCollection:
    """A Smart Collection with two rule groups."""
    return SmartCollection(
        collection_id=42,
        name="Hybrid Collection",
        description="LEGO-Linux OR Action-HighReview",
        icon="\U0001f9e0",
        logic=LogicOperator.OR,
        groups=[
            SmartCollectionRuleGroup(
                logic=LogicOperator.AND,
                rules=(
                    SmartCollectionRule(field=FilterField.TAG, operator=Operator.CONTAINS, value="LEGO"),
                    SmartCollectionRule(field=FilterField.PLATFORM, operator=Operator.EQUALS, value="linux"),
                ),
            ),
            SmartCollectionRuleGroup(
                logic=LogicOperator.AND,
                rules=(
                    SmartCollectionRule(field=FilterField.GENRE, operator=Operator.CONTAINS, value="Action"),
                    SmartCollectionRule(field=FilterField.REVIEW_SCORE, operator=Operator.GREATER_EQUAL, value="80"),
                ),
            ),
        ],
        auto_sync=True,
    )


@pytest.fixture
def collection_flat_rules() -> SmartCollection:
    """A legacy Smart Collection with flat rules (no groups)."""
    return SmartCollection(
        collection_id=10,
        name="Flat Legacy",
        description="Simple OR rules",
        logic=LogicOperator.OR,
        rules=[
            SmartCollectionRule(field=FilterField.TAG, operator=Operator.CONTAINS, value="Indie"),
            SmartCollectionRule(field=FilterField.TAG, operator=Operator.CONTAINS, value="RPG"),
        ],
        auto_sync=False,
    )


# ========================================================================
# EXPORTER TESTS
# ========================================================================


class TestExporterV11:
    """Tests for SmartCollectionExporter with groups."""

    def test_export_with_groups_has_groups_key(
        self, export_path: Path, collection_with_groups: SmartCollection
    ) -> None:
        """Export with groups produces 'groups' key, not 'rules'."""
        SmartCollectionExporter.export([collection_with_groups], export_path)
        with open(export_path, encoding="utf-8") as fh:
            data = json.load(fh)
        sc = data["smart_collections"][0]
        assert "groups" in sc
        assert "rules" not in sc

    def test_export_with_groups_structure(self, export_path: Path, collection_with_groups: SmartCollection) -> None:
        """Exported groups have correct structure."""
        SmartCollectionExporter.export([collection_with_groups], export_path)
        with open(export_path, encoding="utf-8") as fh:
            data = json.load(fh)
        sc = data["smart_collections"][0]
        assert len(sc["groups"]) == 2
        assert sc["groups"][0]["logic"] == "AND"
        assert len(sc["groups"][0]["rules"]) == 2
        assert sc["groups"][0]["rules"][0]["field"] == "tag"

    def test_export_without_groups_has_rules_key(
        self, export_path: Path, collection_flat_rules: SmartCollection
    ) -> None:
        """Export without groups falls back to 'rules' key."""
        SmartCollectionExporter.export([collection_flat_rules], export_path)
        with open(export_path, encoding="utf-8") as fh:
            data = json.load(fh)
        sc = data["smart_collections"][0]
        assert "rules" in sc
        assert "groups" not in sc

    def test_export_version_is_1_1(self, export_path: Path, collection_with_groups: SmartCollection) -> None:
        """Export format version is 1.1."""
        SmartCollectionExporter.export([collection_with_groups], export_path)
        with open(export_path, encoding="utf-8") as fh:
            data = json.load(fh)
        assert data["version"] == "1.1"

    def test_export_no_collection_id(self, export_path: Path, collection_with_groups: SmartCollection) -> None:
        """Exported data does not include collection_id."""
        SmartCollectionExporter.export([collection_with_groups], export_path)
        with open(export_path, encoding="utf-8") as fh:
            data = json.load(fh)
        sc = data["smart_collections"][0]
        assert "collection_id" not in sc


# ========================================================================
# IMPORTER TESTS
# ========================================================================


class TestImporterV11:
    """Tests for SmartCollectionImporter with groups."""

    def test_import_v11_groups(self, export_path: Path, collection_with_groups: SmartCollection) -> None:
        """v1.1 import correctly parses groups."""
        SmartCollectionExporter.export([collection_with_groups], export_path)
        imported = SmartCollectionImporter.import_collections(export_path)
        assert len(imported) == 1
        sc = imported[0]
        assert len(sc.groups) == 2
        assert sc.groups[0].logic == LogicOperator.AND
        assert len(sc.groups[0].rules) == 2
        assert sc.groups[0].rules[0].field == FilterField.TAG

    def test_import_v10_flat_rules(self, tmp_path: Path) -> None:
        """v1.0 import with flat rules still works."""
        v10_data = {
            "version": "1.0",
            "count": 1,
            "smart_collections": [
                {
                    "name": "Old Style",
                    "logic": "OR",
                    "rules": [
                        {"field": "tag", "operator": "contains", "value": "Indie", "value_max": "", "negated": False},
                    ],
                    "auto_sync": True,
                }
            ],
        }
        file_path = tmp_path / "v10.json"
        with open(file_path, "w", encoding="utf-8") as fh:
            json.dump(v10_data, fh)

        imported = SmartCollectionImporter.import_collections(file_path)
        assert len(imported) == 1
        sc = imported[0]
        assert len(sc.rules) == 1
        assert sc.groups == []
        assert sc.rules[0].field == FilterField.TAG

    def test_import_preserves_metadata(self, export_path: Path, collection_with_groups: SmartCollection) -> None:
        """Import preserves name, description, icon, logic, auto_sync."""
        SmartCollectionExporter.export([collection_with_groups], export_path)
        imported = SmartCollectionImporter.import_collections(export_path)
        sc = imported[0]
        assert sc.name == "Hybrid Collection"
        assert sc.description == "LEGO-Linux OR Action-HighReview"
        assert sc.icon == "\U0001f9e0"
        assert sc.logic == LogicOperator.OR
        assert sc.auto_sync is True

    def test_import_collection_id_is_zero(self, export_path: Path, collection_with_groups: SmartCollection) -> None:
        """Imported collections have collection_id=0 (ready for DB creation)."""
        SmartCollectionExporter.export([collection_with_groups], export_path)
        imported = SmartCollectionImporter.import_collections(export_path)
        assert imported[0].collection_id == 0


# ========================================================================
# ROUNDTRIP TESTS
# ========================================================================


class TestRoundtrip:
    """Tests for export -> import roundtrip with groups."""

    def test_groups_roundtrip(self, export_path: Path, collection_with_groups: SmartCollection) -> None:
        """Full roundtrip preserves group structure."""
        SmartCollectionExporter.export([collection_with_groups], export_path)
        imported = SmartCollectionImporter.import_collections(export_path)
        sc = imported[0]

        # Top-level
        assert sc.logic == LogicOperator.OR
        assert len(sc.groups) == 2

        # Group 1
        g1 = sc.groups[0]
        assert g1.logic == LogicOperator.AND
        assert len(g1.rules) == 2
        assert g1.rules[0].field == FilterField.TAG
        assert g1.rules[0].value == "LEGO"
        assert g1.rules[1].field == FilterField.PLATFORM
        assert g1.rules[1].value == "linux"

        # Group 2
        g2 = sc.groups[1]
        assert g2.logic == LogicOperator.AND
        assert len(g2.rules) == 2
        assert g2.rules[0].field == FilterField.GENRE
        assert g2.rules[0].value == "Action"
        assert g2.rules[1].field == FilterField.REVIEW_SCORE
        assert g2.rules[1].value == "80"

    def test_mixed_export_import(
        self,
        export_path: Path,
        collection_with_groups: SmartCollection,
        collection_flat_rules: SmartCollection,
    ) -> None:
        """Export+import of mixed groups and flat rules."""
        SmartCollectionExporter.export([collection_with_groups, collection_flat_rules], export_path)
        imported = SmartCollectionImporter.import_collections(export_path)
        assert len(imported) == 2

        # First: groups
        assert len(imported[0].groups) == 2
        assert imported[0].rules == []

        # Second: flat rules
        assert len(imported[1].rules) == 2
        assert imported[1].groups == []
