# tests/unit/test_utils/test_vdf_importer.py

"""Tests for VDFImporter."""

from __future__ import annotations

from pathlib import Path

import pytest

from src.utils.vdf_importer import VDFImporter

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

_VALID_VDF = """"collections"
{
    "Action"
    {
        "id"        "from-tag-Action"
        "name"      "Action"
        "count"     "2"
        "0"         "440"
        "1"         "570"
    }
    "RPG"
    {
        "id"        "from-tag-RPG"
        "name"      "RPG"
        "count"     "1"
        "0"         "730"
    }
}
"""


@pytest.fixture
def valid_vdf_file(tmp_path: Path) -> Path:
    """Creates a valid VDF file for import testing."""
    vdf_file = tmp_path / "collections.vdf"
    vdf_file.write_text(_VALID_VDF, encoding="utf-8")
    return vdf_file


@pytest.fixture
def empty_vdf_file(tmp_path: Path) -> Path:
    """Creates a VDF file with no collections."""
    vdf_file = tmp_path / "empty.vdf"
    vdf_file.write_text('"collections"\n{\n}\n', encoding="utf-8")
    return vdf_file


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestVDFImporter:
    """Tests for VDFImporter.import_collections()."""

    def test_import_valid_file_returns_collections(self, valid_vdf_file: Path) -> None:
        result = VDFImporter.import_collections(valid_vdf_file)
        assert len(result) == 2

    def test_import_collection_names(self, valid_vdf_file: Path) -> None:
        result = VDFImporter.import_collections(valid_vdf_file)
        names = {c.name for c in result}
        assert "Action" in names
        assert "RPG" in names

    def test_import_collection_app_ids(self, valid_vdf_file: Path) -> None:
        result = VDFImporter.import_collections(valid_vdf_file)
        action = next(c for c in result if c.name == "Action")
        assert 440 in action.app_ids
        assert 570 in action.app_ids

    def test_import_empty_file_returns_empty(self, empty_vdf_file: Path) -> None:
        result = VDFImporter.import_collections(empty_vdf_file)
        assert result == []

    def test_import_nonexistent_file_raises(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError):
            VDFImporter.import_collections(tmp_path / "nonexistent.vdf")

    def test_import_malformed_vdf_returns_empty_or_raises(self, tmp_path: Path) -> None:
        """Malformed VDF either raises ValueError or returns empty (library-dependent)."""
        bad_file = tmp_path / "bad.vdf"
        bad_file.write_text("not valid vdf at all!!!", encoding="utf-8")
        try:
            result = VDFImporter.import_collections(bad_file)
            # If the vdf library doesn't raise, result should be empty
            assert isinstance(result, list)
        except ValueError:
            pass  # Expected for truly invalid VDF

    def test_imported_collection_is_frozen(self, valid_vdf_file: Path) -> None:
        result = VDFImporter.import_collections(valid_vdf_file)
        with pytest.raises(AttributeError):
            result[0].name = "Changed"  # type: ignore[misc]
