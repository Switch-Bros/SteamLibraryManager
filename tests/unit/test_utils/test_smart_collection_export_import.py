# tests/unit/test_utils/test_smart_collection_export_import.py

"""Tests for Smart Collection JSON export and import."""

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
)
from src.utils.smart_collection_exporter import SmartCollectionExporter
from src.utils.smart_collection_importer import SmartCollectionImporter

# ---------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------


@pytest.fixture()
def sample_collections() -> list[SmartCollection]:
    """Returns two sample Smart Collections for testing."""
    return [
        SmartCollection(
            collection_id=1,
            name="LEGO und Star Wars",
            description="LEGO or Star Wars tags",
            icon="\U0001f9e0",
            logic=LogicOperator.OR,
            rules=[
                SmartCollectionRule(
                    field=FilterField.TAG,
                    operator=Operator.CONTAINS,
                    value="LEGO",
                ),
                SmartCollectionRule(
                    field=FilterField.TAG,
                    operator=Operator.CONTAINS,
                    value="Star Wars",
                ),
            ],
            auto_sync=True,
        ),
        SmartCollection(
            collection_id=2,
            name="Lange RPGs",
            description="RPGs with > 50h playtime",
            icon="\U0001f3ae",
            logic=LogicOperator.AND,
            rules=[
                SmartCollectionRule(
                    field=FilterField.GENRE,
                    operator=Operator.CONTAINS,
                    value="RPG",
                ),
                SmartCollectionRule(
                    field=FilterField.PLAYTIME_HOURS,
                    operator=Operator.GREATER_THAN,
                    value="50",
                ),
            ],
            auto_sync=False,
        ),
    ]


@pytest.fixture()
def export_path(tmp_path: Path) -> Path:
    """Returns a temporary file path for export tests."""
    return tmp_path / "smart_collections_export.json"


# ---------------------------------------------------------------
# Exporter Tests
# ---------------------------------------------------------------


class TestSmartCollectionExporter:
    """Tests for SmartCollectionExporter."""

    def test_export_creates_file(self, sample_collections: list[SmartCollection], export_path: Path) -> None:
        """Exported file must exist on disk."""
        SmartCollectionExporter.export(sample_collections, export_path)
        assert export_path.exists()

    def test_export_valid_json(self, sample_collections: list[SmartCollection], export_path: Path) -> None:
        """Exported file must be valid JSON."""
        SmartCollectionExporter.export(sample_collections, export_path)
        data = json.loads(export_path.read_text(encoding="utf-8"))
        assert isinstance(data, dict)

    def test_export_has_version(self, sample_collections: list[SmartCollection], export_path: Path) -> None:
        """Exported JSON must contain a version field."""
        SmartCollectionExporter.export(sample_collections, export_path)
        data = json.loads(export_path.read_text(encoding="utf-8"))
        assert data["version"] == "1.1"

    def test_export_correct_count(self, sample_collections: list[SmartCollection], export_path: Path) -> None:
        """Count field must match the number of exported collections."""
        SmartCollectionExporter.export(sample_collections, export_path)
        data = json.loads(export_path.read_text(encoding="utf-8"))
        assert data["count"] == 2
        assert len(data["smart_collections"]) == 2

    def test_export_collection_fields(self, sample_collections: list[SmartCollection], export_path: Path) -> None:
        """Each exported collection must have name, logic, and rules."""
        SmartCollectionExporter.export(sample_collections, export_path)
        data = json.loads(export_path.read_text(encoding="utf-8"))

        first = data["smart_collections"][0]
        assert first["name"] == "LEGO und Star Wars"
        assert first["description"] == "LEGO or Star Wars tags"
        assert first["logic"] == "OR"
        assert first["auto_sync"] is True
        assert len(first["rules"]) == 2

    def test_export_rule_fields(self, sample_collections: list[SmartCollection], export_path: Path) -> None:
        """Each exported rule must have field, operator, value."""
        SmartCollectionExporter.export(sample_collections, export_path)
        data = json.loads(export_path.read_text(encoding="utf-8"))

        rule = data["smart_collections"][0]["rules"][0]
        assert rule["field"] == "tag"
        assert rule["operator"] == "contains"
        assert rule["value"] == "LEGO"
        assert rule["negated"] is False

    def test_export_empty_list(self, export_path: Path) -> None:
        """Exporting an empty list must produce valid JSON with count 0."""
        SmartCollectionExporter.export([], export_path)
        data = json.loads(export_path.read_text(encoding="utf-8"))
        assert data["count"] == 0
        assert data["smart_collections"] == []

    def test_export_creates_parent_dirs(self, tmp_path: Path) -> None:
        """Exporter must create parent directories if they don't exist."""
        deep_path = tmp_path / "a" / "b" / "c" / "export.json"
        SmartCollectionExporter.export([], deep_path)
        assert deep_path.exists()

    def test_export_excludes_collection_id(self, sample_collections: list[SmartCollection], export_path: Path) -> None:
        """Exported JSON must NOT include collection_id (not portable)."""
        SmartCollectionExporter.export(sample_collections, export_path)
        data = json.loads(export_path.read_text(encoding="utf-8"))
        first = data["smart_collections"][0]
        assert "collection_id" not in first

    def test_export_preserves_icon(self, sample_collections: list[SmartCollection], export_path: Path) -> None:
        """Exported collection must preserve the icon emoji."""
        SmartCollectionExporter.export(sample_collections, export_path)
        data = json.loads(export_path.read_text(encoding="utf-8"))
        second = data["smart_collections"][1]
        assert second["icon"] == "\U0001f3ae"


# ---------------------------------------------------------------
# Importer Tests
# ---------------------------------------------------------------


class TestSmartCollectionImporter:
    """Tests for SmartCollectionImporter."""

    def _write_json(self, path: Path, data: dict) -> None:
        """Helper to write a JSON file for testing."""
        path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")

    def test_import_from_exported_file(self, sample_collections: list[SmartCollection], export_path: Path) -> None:
        """Roundtrip: export then import must preserve all collections."""
        SmartCollectionExporter.export(sample_collections, export_path)
        imported = SmartCollectionImporter.import_collections(export_path)
        assert len(imported) == 2

    def test_import_preserves_name(self, sample_collections: list[SmartCollection], export_path: Path) -> None:
        """Imported collection name must match exported name."""
        SmartCollectionExporter.export(sample_collections, export_path)
        imported = SmartCollectionImporter.import_collections(export_path)
        assert imported[0].name == "LEGO und Star Wars"
        assert imported[1].name == "Lange RPGs"

    def test_import_preserves_logic(self, sample_collections: list[SmartCollection], export_path: Path) -> None:
        """Imported collection logic must match exported logic."""
        SmartCollectionExporter.export(sample_collections, export_path)
        imported = SmartCollectionImporter.import_collections(export_path)
        assert imported[0].logic == LogicOperator.OR
        assert imported[1].logic == LogicOperator.AND

    def test_import_preserves_rules(self, sample_collections: list[SmartCollection], export_path: Path) -> None:
        """Imported rules must match exported rules."""
        SmartCollectionExporter.export(sample_collections, export_path)
        imported = SmartCollectionImporter.import_collections(export_path)
        assert len(imported[0].rules) == 2
        assert imported[0].rules[0].field == FilterField.TAG
        assert imported[0].rules[0].operator == Operator.CONTAINS
        assert imported[0].rules[0].value == "LEGO"

    def test_import_preserves_auto_sync(self, sample_collections: list[SmartCollection], export_path: Path) -> None:
        """Imported auto_sync must match exported auto_sync."""
        SmartCollectionExporter.export(sample_collections, export_path)
        imported = SmartCollectionImporter.import_collections(export_path)
        assert imported[0].auto_sync is True
        assert imported[1].auto_sync is False

    def test_import_preserves_description(self, sample_collections: list[SmartCollection], export_path: Path) -> None:
        """Imported description must match exported description."""
        SmartCollectionExporter.export(sample_collections, export_path)
        imported = SmartCollectionImporter.import_collections(export_path)
        assert imported[0].description == "LEGO or Star Wars tags"

    def test_import_collection_id_is_zero(self, sample_collections: list[SmartCollection], export_path: Path) -> None:
        """Imported collections must have collection_id=0 (ready for creation)."""
        SmartCollectionExporter.export(sample_collections, export_path)
        imported = SmartCollectionImporter.import_collections(export_path)
        assert all(sc.collection_id == 0 for sc in imported)

    def test_import_nonexistent_file_raises(self, tmp_path: Path) -> None:
        """Importing from a nonexistent file must raise FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            SmartCollectionImporter.import_collections(tmp_path / "nope.json")

    def test_import_invalid_json_raises(self, tmp_path: Path) -> None:
        """Importing invalid JSON must raise ValueError."""
        bad_file = tmp_path / "bad.json"
        bad_file.write_text("not json{{{", encoding="utf-8")
        with pytest.raises(ValueError, match="Invalid JSON"):
            SmartCollectionImporter.import_collections(bad_file)

    def test_import_missing_key_raises(self, tmp_path: Path) -> None:
        """Importing JSON without smart_collections key must raise ValueError."""
        bad_file = tmp_path / "no_key.json"
        self._write_json(bad_file, {"version": "1.0", "count": 0})
        with pytest.raises(ValueError, match="Missing"):
            SmartCollectionImporter.import_collections(bad_file)

    def test_import_empty_collections_list(self, tmp_path: Path) -> None:
        """Importing an empty collections list must return empty list."""
        empty_file = tmp_path / "empty.json"
        self._write_json(empty_file, {"version": "1.0", "count": 0, "smart_collections": []})
        result = SmartCollectionImporter.import_collections(empty_file)
        assert result == []

    def test_import_skips_invalid_entries(self, tmp_path: Path) -> None:
        """Invalid entries in the list must be skipped, not cause a crash."""
        mixed_file = tmp_path / "mixed.json"
        self._write_json(
            mixed_file,
            {
                "version": "1.0",
                "count": 2,
                "smart_collections": [
                    {"name": "", "rules": []},  # Invalid: empty name
                    {
                        "name": "Valid One",
                        "logic": "OR",
                        "rules": [{"field": "tag", "operator": "contains", "value": "RPG"}],
                    },
                ],
            },
        )
        result = SmartCollectionImporter.import_collections(mixed_file)
        assert len(result) == 1
        assert result[0].name == "Valid One"

    def test_import_unknown_logic_defaults_to_or(self, tmp_path: Path) -> None:
        """Unknown logic operator must default to OR."""
        file = tmp_path / "unknown_logic.json"
        self._write_json(
            file,
            {
                "version": "1.0",
                "count": 1,
                "smart_collections": [
                    {
                        "name": "Test",
                        "logic": "XOR",
                        "rules": [{"field": "tag", "operator": "contains", "value": "x"}],
                    }
                ],
            },
        )
        result = SmartCollectionImporter.import_collections(file)
        assert result[0].logic == LogicOperator.OR


# ---------------------------------------------------------------
# Roundtrip Tests
# ---------------------------------------------------------------


class TestExportImportRoundtrip:
    """Tests that export → import preserves all data exactly."""

    def test_full_roundtrip_two_collections(self, sample_collections: list[SmartCollection], export_path: Path) -> None:
        """Full roundtrip must preserve name, logic, rules, description, icon, auto_sync."""
        SmartCollectionExporter.export(sample_collections, export_path)
        imported = SmartCollectionImporter.import_collections(export_path)

        for orig, imp in zip(sample_collections, imported):
            assert imp.name == orig.name
            assert imp.description == orig.description
            assert imp.icon == orig.icon
            assert imp.logic == orig.logic
            assert imp.auto_sync == orig.auto_sync
            assert len(imp.rules) == len(orig.rules)
            for orig_rule, imp_rule in zip(orig.rules, imp.rules):
                assert imp_rule.field == orig_rule.field
                assert imp_rule.operator == orig_rule.operator
                assert imp_rule.value == orig_rule.value
                assert imp_rule.value_max == orig_rule.value_max
                assert imp_rule.negated == orig_rule.negated

    def test_roundtrip_with_negated_rules(self, export_path: Path) -> None:
        """Roundtrip must preserve negated flag on rules."""
        collections = [
            SmartCollection(
                name="Not Horror",
                logic=LogicOperator.AND,
                rules=[
                    SmartCollectionRule(
                        field=FilterField.TAG,
                        operator=Operator.CONTAINS,
                        value="Horror",
                        negated=True,
                    ),
                ],
            ),
        ]
        SmartCollectionExporter.export(collections, export_path)
        imported = SmartCollectionImporter.import_collections(export_path)
        assert imported[0].rules[0].negated is True

    def test_roundtrip_with_between_operator(self, export_path: Path) -> None:
        """Roundtrip must preserve value_max for BETWEEN operator."""
        collections = [
            SmartCollection(
                name="2020-2025 Releases",
                logic=LogicOperator.AND,
                rules=[
                    SmartCollectionRule(
                        field=FilterField.RELEASE_YEAR,
                        operator=Operator.BETWEEN,
                        value="2020",
                        value_max="2025",
                    ),
                ],
            ),
        ]
        SmartCollectionExporter.export(collections, export_path)
        imported = SmartCollectionImporter.import_collections(export_path)
        assert imported[0].rules[0].value == "2020"
        assert imported[0].rules[0].value_max == "2025"
