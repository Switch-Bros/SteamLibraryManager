"""Tests for the VDF text exporter."""

from __future__ import annotations

from pathlib import Path

from src.utils.vdf_exporter import VDFTextExporter


class TestVDFTextExporter:
    """Tests for VDFTextExporter.export_collections."""

    def test_export_empty_collections(self, tmp_path: Path) -> None:
        """Empty collection list produces a valid VDF file."""
        output = tmp_path / "empty.vdf"
        VDFTextExporter.export_collections([], output)

        assert output.exists()
        content = output.read_text()
        assert "collections" in content

    def test_export_single_collection_format(self, tmp_path: Path) -> None:
        """Single collection is exported with correct structure."""
        collections = [
            {
                "id": "from-tag-Action",
                "name": "Action",
                "added": [440, 570, 730],
                "removed": [],
            }
        ]
        output = tmp_path / "single.vdf"
        VDFTextExporter.export_collections(collections, output)

        content = output.read_text()
        assert "Action" in content
        assert "from-tag-Action" in content
        assert "440" in content
        assert "570" in content
        assert "730" in content

    def test_export_creates_file_on_disk(self, tmp_path: Path) -> None:
        """Export creates the file and parent directories."""
        nested_path = tmp_path / "sub" / "dir" / "export.vdf"
        collections = [{"name": "RPG", "id": "rpg", "added": [12345]}]

        VDFTextExporter.export_collections(collections, nested_path)

        assert nested_path.exists()
        assert nested_path.stat().st_size > 0

    def test_export_special_characters_escaped(self, tmp_path: Path) -> None:
        """Collection names with special characters are handled correctly."""
        collections = [
            {
                "name": "Tom's Games & More",
                "id": "special-chars",
                "added": [999],
            }
        ]
        output = tmp_path / "special.vdf"
        VDFTextExporter.export_collections(collections, output)

        content = output.read_text()
        # VDF library escapes single quotes as \'
        assert "Tom" in content
        assert "Games & More" in content
        assert "999" in content

    def test_export_multiple_collections(self, tmp_path: Path) -> None:
        """Multiple collections are all exported."""
        collections = [
            {"name": "Action", "id": "action", "added": [440]},
            {"name": "RPG", "id": "rpg", "added": [570]},
            {"name": "Strategy", "id": "strategy", "added": [730]},
        ]
        output = tmp_path / "multi.vdf"
        VDFTextExporter.export_collections(collections, output)

        content = output.read_text()
        assert "Action" in content
        assert "RPG" in content
        assert "Strategy" in content
